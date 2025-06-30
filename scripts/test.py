import skia


def draw_from_raw_affine_m44(canvas):
    """
    Draws a shape by constructing a 2D affine SkM44 from raw 9 values.
    """
    canvas.clear(skia.ColorWHITE)

    # Example 2D affine 4x4 matrix (translate 50,50 and scale 0.5,0.5)
    # This corresponds to:
    # [ 0.5, 0.0, 0.0, 50.0 ]
    # [ 0.0, 0.5, 0.0, 50.0 ]
    # [ 0.0, 0.0, 1.0, 0.0  ]
    # [ 0.0, 0.0, 0.0, 1.0  ]

    # Extract the 9 values for skia.Matrix.MakeAll
    # MakeAll takes: (scaleX, skewX, transX, skewY, scaleY, transY, persp0, persp1, persp2)
    # From the 4x4 matrix, these map to:
    # m00, m01, m03 (transX)
    # m10, m11, m13 (transY)
    # m30, m31, m33 (persp2) - note: m32 is usually 0 for 2D, but MakeAll takes a 9th for m22

    # Let's target a simple scale and translate
    scale_x = 0.5
    scale_y = 0.5
    trans_x = 50.0
    trans_y = 50.0

    # The 9 values for skia.Matrix.MakeAll:
    # (scaleX, skewX, transX, skewY, scaleY, transY, persp0, persp1, persp2)
    m_9_values = (
        scale_x,
        0.0,
        trans_x,  # Row 0: scaleX, skewX, transX
        0.0,
        scale_y,
        trans_y,  # Row 1: skewY, scaleY, transY
        0.0,
        0.0,
        1.0,  # Row 2: persp0, persp1, persp2 (typically for 2D affine)
    )

    # Create an SkMatrix (3x3)
    sk_matrix_3x3 = skia.Matrix.MakeAll(*m_9_values)

    # Convert the SkMatrix to SkM44
    m44 = skia.M44(sk_matrix_3x3)

    print(f'Constructed SkM44 from SkMatrix:\n{m44}')

    # Apply the matrix to the canvas
    canvas.concat(m44)

    paint = skia.Paint(
        Style=skia.Paint.kFill_Style,
        AntiAlias=True,
        Color=0xFF4285F4,  # Blue
    )
    canvas.drawRect(skia.Rect.MakeXYWH(0, 0, 100, 100), paint)


# Create a surface and draw
surface = skia.Surface(300, 250)
with surface as canvas:
    draw_from_raw_affine_m44(canvas)

# Save the image
image = surface.makeImageSnapshot()
image.save('affine_m44_from_matrix.png')

print('Image saved to affine_m44_from_matrix.png')
