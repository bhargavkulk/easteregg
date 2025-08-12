open Classical

-- The basic indexing type
def Point : Type := Unit

-- Color := (alpha, red, green, blue)
def Color : Type := (Float × Float × Float × Float)

def Transparent : Color :=  (0.0, 0.0, 0.0, 0.0)

-- Geometry is a collection of points
abbrev Geometry := Point -> Bool

-- Style changes the geometry
abbrev Style := Geometry -> Geometry

-- Paintdraw defines how a geometry is painted
abbrev PaintDraw := Style × (Point -> Color)

-- BlendMode blends 2 colors together
abbrev BlendMode := Color -> Color -> Color
--- SrcOver is a blend mode: r = s + (1-sa)*d
axiom SrcOver : BlendMode
axiom SrcOver_left_transparent:
  forall c : Color, SrcOver c Transparent = c
axiom SrcOver_right_transparent :
  forall c : Color, SrcOver Transparent c = c
axiom SrcOver_associative :
  forall c₁ c₂ c₃ : Color, SrcOver (SrcOver c₁ c₂) c₃ = SrcOver c₁ (SrcOver c₂ c₃)

-- PaintBlend defines how 2 layers are blended together
abbrev PaintBlend := (Float × BlendMode)

-- A layer is a buffer of pixels
abbrev Layer := Point -> Color

-- applyalpha applies an alpha across a layer
axiom applyAlpha : Float -> Color -> Color
axiom applyAlpha_opaque :
  forall c : Color, applyAlpha 1.0 c = c
axiom applyAlpha_transparent :
  forall c : Color, applyAlpha 0.0 c = Transparent
axiom applyAlpha_on_transparent :
  forall a : Float, applyAlpha a Transparent = Transparent

noncomputable def blend  (l₁ l₂ : Layer) (pb: PaintBlend) (clip : Geometry) : Layer :=
  let (α, bm) := pb
  fun pt => if (clip pt) then bm (l₁ pt) (applyAlpha α (l₂ pt)) else (l₁ pt)

  -- rasterizes a geometry into a layer
noncomputable def raster (shape: Geometry) (paint: PaintDraw) : Layer :=
  let (style, color) := paint
  fun pt => if (style shape) pt then color pt else Transparent

-- Now we define layers
-- Empty()
def EmptyLayer : Layer := (fun _ => Transparent)

-- SaveLayer blends a layer onto another layer
-- l₁ bottom layer
-- l₂ top layer
noncomputable def SaveLayer (l₁ l₂ : Layer) (pb : PaintBlend) : Layer :=
  blend l₁ l₂ pb (fun _ => true)

theorem empty_SrcOver_SaveLayer_is_Empty l:
  SaveLayer l EmptyLayer (1.0, SrcOver) = l := by
  unfold SaveLayer
  unfold EmptyLayer
  simp [blend]
  ext pt
  simp [applyAlpha_opaque]
  simp [SrcOver_left_transparent]

-- now we define draw
noncomputable def Draw (l : Layer) (g : Geometry) (pd : PaintDraw) (pb : PaintBlend) (clip : Geometry): Layer :=
  blend l (raster g pd) pb clip

theorem lone_draw_inside_opaque_srcover_savelayer
  (bottom : Layer) (g : Geometry) (pd : PaintDraw) (α: Float) (c : Geometry):
  SaveLayer bottom (Draw EmptyLayer g pd (α, SrcOver) c) (1.0, SrcOver) = Draw bottom g pd (α, SrcOver) c := by
  unfold SaveLayer
  unfold Draw
  unfold EmptyLayer
  simp [blend]
  ext pt
  cases (c pt) with
  | true =>
    simp [SrcOver_right_transparent]
    simp [applyAlpha_opaque]
  | false =>
    simp [applyAlpha_on_transparent]
    simp [SrcOver_left_transparent]

theorem last_draw_inside_opaque_srcover_savelayer
  (l₁ l₂ : Layer) (g c : Geometry) (pd : PaintDraw) (α : Float) :
  SaveLayer l₁ (Draw l₂ g pd (α, SrcOver) c) (1.0, SrcOver) = Draw (SaveLayer l₁ l₂ (1.0, SrcOver)) g pd (α, SrcOver) c := by
  unfold SaveLayer Draw
  simp [blend]
  ext pt
  cases (c pt) with
  | true =>
    simp [applyAlpha_opaque]
    simp [SrcOver_associative]
  | false => trivial

theorem last_draw_inside_opaque_srcover_savelayer_2
  (l₁ l₂ : Layer) (g c : Geometry) (pd : PaintDraw) (α₁ α₂ : Float) :
  SaveLayer l₁ (Draw l₂ g pd (α₂, SrcOver) c) (α₁, SrcOver) = Draw (SaveLayer l₁ l₂ (α₁, SrcOver)) g pd (α₂, SrcOver) c := by
  unfold SaveLayer Draw
  simp [blend]
  ext pt
  cases (c pt) with
  | true =>
    simp [applyAlpha_opaque]
    simp [SrcOver_associative]

  | false => trivial
