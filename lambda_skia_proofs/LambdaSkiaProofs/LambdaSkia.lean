open Classical

-- The basic indexing type
def Point : Type := Unit

-- The transform matrix (multiplication is implicit)
def Transform: Type := Point -> Point

-- Color := (alpha, red, green, blue)
def Color : Type := (Float × Float × Float × Float)

def Transparent : Color := (0.0, 0.0, 0.0, 0.0)

-- Geometry is a collection of points
abbrev Geometry := Point -> Bool

-- Style changes the geometry
abbrev Style := Geometry -> Geometry

-- Color Filters
abbrev ColorFilter := Color -> Color

-- Paintdraw defines how a geometry is painted
abbrev PaintDraw := Style × (Point -> Color) × ColorFilter

-- BlendMode blends 2 colors together
-- These area both easy and annoying to formally prove
-- so we are just going to leave them as axioms.
-- If you want to see the example formalization,
-- see Colors.lean.
abbrev BlendMode := Color -> Color -> Color
--- SrcOver is a blend mode: r = s + (1-sa)*d
axiom SrcOver : BlendMode
@[grind]
axiom SrcOver_left_transparent:
  forall c : Color, SrcOver c Transparent = c
@[grind]
axiom SrcOver_right_transparent :
  forall c : Color, SrcOver Transparent c = c
@[grind]
axiom SrcOver_associative :
  forall c₁ c₂ c₃ : Color, SrcOver (SrcOver c₁ c₂) c₃ = SrcOver c₁ (SrcOver c₂ c₃)

-- PaintBlend defines how 2 layers are blended together
abbrev PaintBlend := (Float × BlendMode)

-- A layer is a buffer of pixels
abbrev Layer := Point -> Color

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

@[grind]
noncomputable def blend  (l₁ l₂ : Layer) (pb: PaintBlend) (clip : Geometry) : Layer :=
  let (α, bm) := pb
  fun pt => if (clip pt) then bm (l₁ pt) (applyAlpha α (l₂ pt)) else (l₁ pt)

  -- rasterizes a geometry into a layer
@[grind]
noncomputable def raster (shape: Geometry) (paint: PaintDraw) (t: Transform) : Layer :=
  let (style, color, color_filter) := paint
  fun pt =>
  let pt := (t pt)
  if (style shape) pt then color_filter (color pt) else Transparent

-- Now we define layers
-- Empty()
@[grind]
def EmptyLayer : Layer := (fun _ => Transparent)

-- SaveLayer blends a layer onto another layer
-- l₁ bottom layer
-- l₂ top layer
@[grind]
noncomputable def SaveLayer (l₁ l₂ : Layer) (pb : PaintBlend) : Layer :=
  blend l₁ l₂ pb (fun _ => true)

theorem empty_SrcOver_SaveLayer_is_Empty l:
  SaveLayer l EmptyLayer (1.0, SrcOver) = l := by grind

-- now we define draw
@[grind]
noncomputable def Draw (l : Layer) (g : Geometry) (pd : PaintDraw) (pb : PaintBlend) (t: Transform)(clip : Geometry): Layer :=
  blend l (raster g pd t) pb clip

theorem lone_draw_inside_opaque_srcover_savelayer
  (bottom : Layer) (g : Geometry) (pd : PaintDraw) (α: Float) (c : Geometry) (t: Transform):
  SaveLayer bottom (Draw EmptyLayer g pd (α, SrcOver) t c) (1.0, SrcOver) = Draw bottom g pd (α, SrcOver) t c := by
  grind

theorem last_draw_inside_opaque_srcover_savelayer
  (l₁ l₂ : Layer) (g c : Geometry) (pd : PaintDraw) (α : Float) (t : Transform):
  SaveLayer l₁ (Draw l₂ g pd (α, SrcOver) t c) (1.0, SrcOver) = Draw (SaveLayer l₁ l₂ (1.0, SrcOver)) g pd (α, SrcOver) t c := by
  grind
