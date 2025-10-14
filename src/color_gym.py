from z3 import *


# ---------- SrcOver function ----------
def SrcOver(dst, src):
    """
    dst, src: tuples of Reals (r, g, b, a)
    returns: tuple of Reals (r_out, g_out, b_out, a_out)
    """
    r_out = src[0] + (1 - src[3]) * dst[0]
    g_out = src[1] + (1 - src[3]) * dst[1]
    b_out = src[2] + (1 - src[3]) * dst[2]
    a_out = src[3] + (1 - src[3]) * dst[3]
    return (r_out, g_out, b_out, a_out)


# ---------- Helper to create premultiplied color ----------
def mk_premul_color(letter, solver):
    """
    Create a symbolic premultiplied color with name prefix 'letter'
    and add premultiplied constraints to the solver.
    Returns: (r, g, b, a) as a tuple of Reals
    """
    r = Real(f'{letter}_r')
    g = Real(f'{letter}_g')
    b = Real(f'{letter}_b')
    a = Real(f'{letter}_a')

    # premultiplied constraints: 0 <= r,g,b <= a <= 1
    solver.add(a >= 0, a <= 1)
    solver.add(r >= 0, r <= a)
    solver.add(g >= 0, g <= a)
    solver.add(b >= 0, b <= a)

    return (r, g, b, a)


# ---------- Helper to prove equality ----------
def prove_eq(solver, lhs, rhs, proposition: str):
    """
    Prove lhs = rhs in Z3.
    """
    print(f'Proving: {proposition}')
    solver.add(Or(lhs[0] != rhs[0], lhs[1] != rhs[1], lhs[2] != rhs[2], lhs[3] != rhs[3]))
    if solver.check() == sat:
        print('Counterexample found:\n', solver.model())
    else:
        print('QED')


# ---------- Z3 solver ----------
s = Solver()

# ---------- SrcOver(c, transparent) ----------
s.push()
c = mk_premul_color('c', s)
transparent = (0.0, 0.0, 0.0, 0.0)
out = SrcOver(c, transparent)
prove_eq(s, out, c, 'SrcOver(c, transparent) = c')
s.pop()

# ---------- SrcOver(transparent, c) ----------
s.push()
out = SrcOver(transparent, c)
prove_eq(s, out, c, 'SrcOver(transparent, c) = c')
s.pop()

# ---------- SrcOver associativity ----------
s.push()
c1 = mk_premul_color('c1', s)
c2 = mk_premul_color('c2', s)
c3 = mk_premul_color('c3', s)
lhs = SrcOver(SrcOver(c1, c2), c3)
rhs = SrcOver(c1, SrcOver(c2, c3))
prove_eq(s, lhs, rhs, 'SrcOver(SrcOver(c1, c2), c3) = SrcOver(c1, SrcOver(c2, c3))')
s.pop()


# ---------- f in Z3 ----------
def f_z3(color):
    r, g, b, a = color
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # clamp to [0,1]
    luma = If(luma < 0.0, 0.0, If(luma > 1.0, 1.0, luma))
    return (0.0, 0.0, 0.0, luma)


# ---------- Test f((0,0,0,1)) = (0,0,0,0) ----------
s.push()
c = mk_premul_color('c', s)
s.add(c[0] == 0.0, c[1] == 0.0, c[2] == 0.0, c[3] == 1.0)

lhs = f_z3(c)
rhs = (0.0, 0.0, 0.0, 0.0)

prove_eq(s, lhs, rhs, 'f((0,0,0,1)) = (0,0,0,0)')
s.pop()

# s.push()
# # symbolic premultiplied colors c1, c2
# c1 = mk_premul_color('c1', s)
# c2 = mk_premul_color('c2', s)

# # compute both sides
# lhs = f_z3(SrcOver(c1, c2))
# rhs = SrcOver(f_z3(c1), f_z3(c2))

# prove_eq(s, lhs, rhs, 'f(SrcOver(c1, c2)) = SrcOver(f(c1), f(c2))')
# s.pop()

s.push()
# symbolic premultiplied color c1
c1 = mk_premul_color('c1', s)

# c2 = white
c2 = (1.0, 1.0, 1.0, 1.0)

# compute both sides
lhs = f_z3(SrcOver(c1, c2))
rhs = SrcOver(f_z3(c1), f_z3(c2))

prove_eq(s, lhs, rhs, 'f(SrcOver(c1, white)) = SrcOver(f(c1), f(white))')
s.pop()

s.push()
# symbolic premultiplied color c1
c1 = mk_premul_color('c1', s)
s.add(c1[3] == 1.0)

# c2 = black
c2 = (0.0, 0.0, 0.0, 1.0)

# compute both sides
lhs = f_z3(SrcOver(c1, c2))
rhs = SrcOver(f_z3(c1), f_z3(c2))

prove_eq(s, lhs, rhs, 'f(SrcOver(c1, black)) = SrcOver(f(c1), f(black))')
s.pop()

# counter example:  [c1_a = 1/2, c1_r = 1/2, c1_b = 0, c1_g = 0]

s.push()
# c1 = white
c1 = (1.0, 1.0, 1.0, 1.0)

# c2 = black
c2 = (0.0, 0.0, 0.0, 1.0)

# compute both sides
lhs = f_z3(SrcOver(c1, c2))
rhs = SrcOver(f_z3(c1), f_z3(c2))

prove_eq(s, lhs, rhs, 'f(SrcOver(white, black)) = SrcOver(f(white), f(black))')
s.pop()
