/-!
# A Core Calculus for Skia

This file defines a core calculus for Skia, a popular 2D graphics library. The calculus includes definitions for colors, blend modes, color filters, geometries, transformations, layers, and paint operations. It also includes axioms that capture the behavior of various blend modes and color operations.
-/

open Classical

@[grind, simp]
def Point : Type := Unit

@[grind, simp]
def Geometry : Type := Point -> Bool

@[grind, simp]
def intersect (g1 g2 : Geometry) : Geometry :=
  fun pt => g1 pt && g2 pt

@[grind, simp]
def difference (g1 g2 : Geometry) : Geometry :=
  fun pt => g1 pt && not (g2 pt)

@[grind, simp]
def Transform : Type := Point -> Point

@[grind, simp]
def Color : Type := (Float × Float × Float × Float)

@[grind, simp]
def Transparent : Color := (0.0, 0.0, 0.0, 0.0)

@[grind, simp]
def BlendMode : Type := Color -> Color -> Color

@[grind, simp]
def ColorFilter : Type := Color -> Color

@[grind, simp]
def PaintBlend := (Float × BlendMode × (Color -> Color))

@[grind, simp]
def PaintDraw := (Geometry -> Geometry) × (Point -> Color)

inductive Layer
| Empty
| SaveLayer (bottom top : Layer) (pb : PaintBlend)
| Draw (bottom : Layer) (shape : Geometry) (pd : PaintDraw) (pb : PaintBlend) (clip : Geometry) (t : Transform)

-- applyalpha applies an alpha across a layer
axiom applyAlpha : Float -> Color -> Color
@[grind]
axiom applyAlpha_opaque :
  forall c : Color, applyAlpha 1.0 c = c
@[grind]
axiom applyAlpha_transparent :
  forall c : Color, applyAlpha 0.0 c = Transparent
@[grind]
axiom applyAlpha_on_transparent :
  forall a : Float, applyAlpha a Transparent = Transparent

@[grind, simp]
noncomputable def denote : Layer -> Point -> Color
| Layer.Empty => fun _ => Transparent
| Layer.SaveLayer bot top pb =>
    fun pt =>
      let (α, blend_mode, color_filter) := pb
      let bottom := denote bot
      let top := denote top
      blend_mode (bottom pt) (applyAlpha α (color_filter (top pt)))
