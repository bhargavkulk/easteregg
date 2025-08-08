import Formalization.Basic

open Classical

-- Dummy inductive types for use in proofs
inductive Point where
  | mk : Nat → Point
  deriving DecidableEq, Repr


inductive Color where
  | argb : Float → Float → Float → Float → Color -- a, r, g, b (premultiplied)
  deriving Repr

-- Geometry is a set of points
abbrev Geometry := Point → Prop

-- style is a function from Geometry to Geometry
abbrev Style := Geometry → Geometry

-- color is a function from Point to Color
abbrev PaintDraw := Style × (Point → Color)


-- Core type definitions
abbrev Layer := Point → Color
abbrev BlendMode := Color → Color → Color

abbrev plaint_blend := (Float × BlendMode)

-- Axiomatized blend mode SrcOver
axiom SrcOver : BlendMode

-- Example axioms for SrcOver (customize as needed)

axiom SrcOver_left_transparent : ∀ c : Color, SrcOver c (Color.argb 0.0 0.0 0.0 0.0) = c
axiom SrcOver_right_transparent : ∀ c : Color, SrcOver (Color.argb 0.0 0.0 0.0 0.0) c = c


def Transparent : Color := Color.argb 0.0 0.0 0.0 0.0

noncomputable def raster (shape : Geometry) (paint : PaintDraw) : Layer :=
  let (style, color) := paint
  let shape_2 := style shape
  (fun pt : Point => if shape_2 pt then color pt else Transparent : Layer)


-- Axiomatized applyAlpha

axiom applyAlpha : Float → Color → Color
axiom applyAlpha_zero : ∀ c : Color, applyAlpha 0.0 c = Color.argb 0.0 0.0 0.0 0.0
axiom applyAlpha_one  : ∀ c : Color, applyAlpha 1.0 c = c
axiom applyAlpha_clip_hi : ∀ (a : Float) (c : Color), a > 1.0 → applyAlpha a c = applyAlpha 1.0 c
axiom applyAlpha_clip_lo : ∀ (a : Float) (c : Color), a < 0.0 → applyAlpha a c = applyAlpha 0.0 c
axiom applyAlpha_idempotent : ∀ α c, applyAlpha α (applyAlpha α c) = applyAlpha α c

noncomputable def blend (α : Float) (bm : BlendMode) (l1 l2 : Layer) : Layer :=
  fun pt => bm (l1 pt) (applyAlpha α (l2 pt))


noncomputable def savelayer (l1 l2 : Layer) (pd : PaintDraw) (pb : plaint_blend) : Layer :=

  blend pb.1 pb.2 l1 l2

-- Draw: blend a layer with a rasterized geometry using the given paint and blend mode
noncomputable def draw (l : Layer) (g : Geometry) (pd : PaintDraw) (pb : plaint_blend) : Layer :=
  blend pb.1 pb.2 l (raster g pd)

-- Theorem: savelayer with SrcOver, empty l1, and alpha = 1.0 is also empty
theorem savelayer_empty_over_opaque_is_empty (l2 : Layer) (pd : PaintDraw) :
  savelayer l2 (fun _ => Transparent) pd (1.0, SrcOver) = l2 :=
  by
    funext pt
    simp [savelayer]
    simp [blend]
    simp [applyAlpha_one]
    simp [Transparent]
    simp [SrcOver_left_transparent]

/-
... l2

-/

-- Theorem: If the last layer inside a savelayer is a draw with opaque alpha and SrcOver, then the draw can be moved outside the savelayer
theorem savelayer_single_draw(l : Layer) (g : Geometry) a (pd : PaintDraw) (pb : plaint_blend) :
  savelayer l (draw (fun _ => Transparent) g pd (a, SrcOver)) pd (1.0, SrcOver)
   = draw l g pd (a, SrcOver) :=
  by
    funext pt
    simp [savelayer]
    simp [draw]
    simp [raster]
    simp [blend]
    simp [applyAlpha_one]
    simp [Transparent]
    simp [SrcOver_right_transparent]
/-
... l2

-/

-- Theorem: If the last layer inside a savelayer is a draw with opaque alpha and SrcOver, then the draw can be moved outside the savelayer
