# ----------------------------
# Utilities: PNG output (scaled)
# ----------------------------
import struct
import zlib
from dataclasses import dataclass

import z3


def write_png(path, rgba, W, H, scale=1):
    """
    rgba: list of (r,g,b,a) uint8, row-major, length W*H
    Writes an RGBA PNG. Optional nearest-neighbor scaling.
    """
    assert len(rgba) == W * H

    if scale > 1:
        scaled = []
        for y in range(H):
            row = rgba[y * W : (y + 1) * W]
            row_scaled = []
            for px in row:
                row_scaled.extend([px] * scale)
            for _ in range(scale):
                scaled.extend(row_scaled)
        rgba = scaled
        W *= scale
        H *= scale

    def png_chunk(typ, data):
        return (
            struct.pack('>I', len(data))
            + typ
            + data
            + struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    # PNG file signature
    out = [b'\x89PNG\r\n\x1a\n']

    # IHDR: width, height, bit depth=8, color type=6 (RGBA)
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 6, 0, 0, 0)
    out.append(png_chunk(b'IHDR', ihdr))

    # Image data: each row prefixed with filter byte 0
    raw = bytearray()
    i = 0
    for y in range(H):
        raw.append(0)  # filter type 0
        for x in range(W):
            r, g, b, a = rgba[i]
            raw.extend([r, g, b, a])
            i += 1

    compressed = zlib.compress(bytes(raw), level=9)
    out.append(png_chunk(b'IDAT', compressed))

    # IEND
    out.append(png_chunk(b'IEND', b''))

    with open(path, 'wb') as f:
        for c in out:
            f.write(c)


# ----------------------------
# Color: 8-bit RGBA (BitVec)
# ----------------------------

Color = z3.Datatype('Color')
Color.declare(
    'mk',
    ('r', z3.BitVecSort(8)),
    ('g', z3.BitVecSort(8)),
    ('b', z3.BitVecSort(8)),
    ('a', z3.BitVecSort(8)),
)
Color = Color.create()


def chan(c, name):
    if name == 'r':
        return Color.r(c)
    if name == 'g':
        return Color.g(c)
    if name == 'b':
        return Color.b(c)
    if name == 'a':
        return Color.a(c)
    raise ValueError(name)


def bv8(x):
    return z3.BitVecVal(x, 8)


def bv16(x):
    return z3.BitVecVal(x, 16)


def u8_to_u16(x8):
    return z3.ZeroExt(8, x8)  # BV16


def clamp_u16_to_u8(x16):
    return z3.If(z3.UGT(x16, bv16(255)), bv8(255), z3.Extract(7, 0, x16))


def mul8_div255(x8, y8):
    prod = u8_to_u16(x8) * u8_to_u16(y8)  # up to 65025
    return z3.Extract(7, 0, z3.UDiv(prod, bv16(255)))


TRANSPARENT = Color.mk(bv8(0), bv8(0), bv8(0), bv8(0))


def src_over(s, d):
    # Simplified integer model: out = s + (1 - sa)*d, /255 scaling, per channel.
    sa = chan(s, 'a')
    inv_sa = z3.BitVecVal(255, 8) - sa

    def blend_chan(sc, dc):
        term = mul8_div255(inv_sa, dc)
        return clamp_u16_to_u8(u8_to_u16(sc) + u8_to_u16(term))

    r = blend_chan(chan(s, 'r'), chan(d, 'r'))
    g = blend_chan(chan(s, 'g'), chan(d, 'g'))
    b = blend_chan(chan(s, 'b'), chan(d, 'b'))

    a_term = mul8_div255(inv_sa, chan(d, 'a'))
    a = clamp_u16_to_u8(u8_to_u16(sa) + u8_to_u16(a_term))
    return Color.mk(r, g, b, a)


# ----------------------------
# Canvas / image
# ----------------------------


@dataclass(frozen=True)
class Canvas:
    W: int
    H: int

    def idx(self, x, y):
        return y * self.W + x


def empty_layer():
    return z3.K(z3.IntSort(), TRANSPARENT)


# ----------------------------
# Symbolic Rect + Color
# ----------------------------


@dataclass(frozen=True)
class SymRect:
    x0: z3.IntNumRef | z3.ArithRef
    y0: z3.IntNumRef | z3.ArithRef
    x1: z3.IntNumRef | z3.ArithRef  # exclusive
    y1: z3.IntNumRef | z3.ArithRef  # exclusive


def rect_constraints(canvas: Canvas, r: SymRect):
    # Non-empty, in-bounds, axis-aligned.
    return z3.And(
        0 <= r.x0, r.x0 < r.x1, r.x1 <= canvas.W, 0 <= r.y0, r.y0 < r.y1, r.y1 <= canvas.H
    )


#
#
def pixel_in_rect(xx, yy, r: SymRect):
    return z3.And(xx >= r.x0, xx < r.x1, yy >= r.y0, yy < r.y1)


@dataclass(frozen=True)
class SymColor:
    r: z3.BitVecRef
    g: z3.BitVecRef
    b: z3.BitVecRef
    a: z3.BitVecRef


def color_term(c: SymColor):
    return Color.mk(c.r, c.g, c.b, c.a)


def color_constraints(c: SymColor):
    # BitVec8 already bounds. You may want to avoid fully transparent to make examples clearer:
    return z3.And(c.a != bv8(0))


# ----------------------------
# Draw: fill rect with solid color, SrcOver
# ----------------------------


def draw_rect_src_over(canvas: Canvas, img, r: SymRect, c: SymColor):
    out = img
    src = color_term(c)

    # Fully unrolled over pixels (quantifier-free)
    for y in range(canvas.H):
        for x in range(canvas.W):
            idx = canvas.idx(z3.IntVal(x), z3.IntVal(y))
            dst = z3.Select(out, idx)
            blended = src_over(src, dst)
            cond = pixel_in_rect(z3.IntVal(x), z3.IntVal(y), r)
            out = z3.Store(out, idx, z3.If(cond, blended, dst))
    return out


# ----------------------------
# Counterexample search + rendering
# ----------------------------


def eval_color_tuple(m, cterm):
    return (
        m.eval(Color.r(cterm), model_completion=True).as_long(),
        m.eval(Color.g(cterm), model_completion=True).as_long(),
        m.eval(Color.b(cterm), model_completion=True).as_long(),
        m.eval(Color.a(cterm), model_completion=True).as_long(),
    )


def image_to_rgba(m, canvas: Canvas, img):
    rgba = []
    for y in range(canvas.H):
        for x in range(canvas.W):
            idx = canvas.idx(z3.IntVal(x), z3.IntVal(y))
            c = m.eval(z3.Select(img, idx), model_completion=True)
            rgba.append(eval_color_tuple(m, c))
    return rgba


def diff_rgba(a, b):
    # magenta where different, transparent where same
    out = []
    for pa, pb in zip(a, b):
        out.append((0, 0, 0, 0) if pa == pb else (255, 0, 255, 255))
    return out


def read_int(m, v):
    return m.eval(v, model_completion=True).as_long()


def read_bv8(m, v):
    return m.eval(v, model_completion=True).as_long()


def print_model(canvas, m, ra, rb, c1, c2):
    A = (read_int(m, ra.x0), read_int(m, ra.y0), read_int(m, ra.x1), read_int(m, ra.y1))
    B = (read_int(m, rb.x0), read_int(m, rb.y0), read_int(m, rb.x1), read_int(m, rb.y1))
    C1 = (read_bv8(m, c1.r), read_bv8(m, c1.g), read_bv8(m, c1.b), read_bv8(m, c1.a))
    C2 = (read_bv8(m, c2.r), read_bv8(m, c2.g), read_bv8(m, c2.b), read_bv8(m, c2.a))
    print('Counterexample:')
    print('  a rect =', A)
    print('  b rect =', B)
    print('  c1     =', C1)
    print('  c2     =', C2)


# ----------------------------
# Main: prove non-commutativity by finding a counterexample
# ----------------------------

if __name__ == '__main__':
    canvas = Canvas(W=8, H=8)

    # Symbolic rectangles a, b
    ax0, ay0, ax1, ay1 = z3.Ints('ax0 ay0 ax1 ay1')
    bx0, by0, bx1, by1 = z3.Ints('bx0 by0 bx1 by1')
    a = SymRect(ax0, ay0, ax1, ay1)
    b = SymRect(bx0, by0, bx1, by1)

    # Symbolic colors c1, c2
    c1 = SymColor(
        z3.BitVec('c1r', 8), z3.BitVec('c1g', 8), z3.BitVec('c1b', 8), z3.BitVec('c1a', 8)
    )
    c2 = SymColor(
        z3.BitVec('c2r', 8), z3.BitVec('c2g', 8), z3.BitVec('c2b', 8), z3.BitVec('c2a', 8)
    )

    base = empty_layer()

    # Source: Draw(a,c1); Draw(b,c2)
    imgS = draw_rect_src_over(canvas, draw_rect_src_over(canvas, base, a, c1), b, c2)

    # Target: Draw(b,c2); Draw(a,c1)
    imgT = draw_rect_src_over(canvas, draw_rect_src_over(canvas, base, b, c2), a, c1)

    # Find counterexample: witness pixel p where images differ (faster than OR-all)
    p = z3.Int('p')

    s = z3.Solver()
    s.add(rect_constraints(canvas, a))
    s.add(rect_constraints(canvas, b))
    s.add(color_constraints(c1))
    s.add(color_constraints(c2))

    # Optional: encourage overlap so counterexample is visually meaningful
    # (Still satisfiable even without, but this helps quality.)
    s.add(
        z3.Exists(
            [z3.Int('xx'), z3.Int('yy')],
            z3.And(
                0 <= z3.Int('xx'),
                z3.Int('xx') < canvas.W,
                0 <= z3.Int('yy'),
                z3.Int('yy') < canvas.H,
                pixel_in_rect(z3.Int('xx'), z3.Int('yy'), a),
                pixel_in_rect(z3.Int('xx'), z3.Int('yy'), b),
            ),
        )
    )

    s.add(p >= 0, p < canvas.W * canvas.H)
    s.add(z3.Select(imgS, p) != z3.Select(imgT, p))

    res = s.check()
    print('SAT means counterexample exists:', res)

    if res == z3.sat:
        m = s.model()
        print_model(canvas, m, a, b, c1, c2)

        rgbaS = image_to_rgba(m, canvas, imgS)
        rgbaT = image_to_rgba(m, canvas, imgT)
        rgbaD = diff_rgba(rgbaS, rgbaT)

        write_png('source.png', rgbaS, canvas.W, canvas.H, scale=32)
        write_png('target.png', rgbaT, canvas.W, canvas.H, scale=32)
        write_png('diff.png', rgbaD, canvas.W, canvas.H, scale=32)

        print('Wrote source.png, target.png, diff.png')
