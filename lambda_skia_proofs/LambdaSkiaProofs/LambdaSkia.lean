open Classical

-- The basic indexing type
@[grind]
def Point : Type := Unit

-- WTF IS TRANFORM DOING
-- IMO there are 2 spaces:
-- * the global coordinate set
-- * the local coordinate set
-- Remember a Layer maps a point to the
-- The transform matrix (multiplication is implicit)
@[grind]
def Transform: Type := Point -> Point

-- Color := (alpha, red, green, blue)
@[grind]
def Color : Type := (Float × Float × Float × Float)

axiom isOpaque (c : Color) : Prop

@[grind]
def Transparent : Color := (0.0, 0.0, 0.0, 0.0)

-- Geometry is a collection of points
abbrev Geometry := Point -> Bool

@[grind]
def intersect (g1 g2 : Geometry) : Geometry :=
  fun pt => g1 pt && g2 pt

-- Style changes the geometry
abbrev Style := Geometry -> Geometry
def Fill : Style := fun g => g

-- Color Filters
abbrev ColorFilter := Color -> Color
@[grind]
def idColorFilter : ColorFilter := fun c => c
-- Paintdraw defines how a geometry is painted
abbrev PaintDraw := Style × (Point -> Color)

-- BlendMode blends 2 colors together
-- These area both easy and annoying to formally prove
-- so we are just going to leave them as axioms.
-- If you want to see the example formalization,
-- see Colors.lean.
abbrev BlendMode := Color -> Color -> Color
--- SrcOver is a blend mode: r = s + (1-sa)*d
axiom SrcOver : BlendMode
-- soflight blend mode
axiom SoftLight : BlendMode
@[grind]
axiom SrcOver_left_transparent:
  forall c : Color, SrcOver c Transparent = c
@[grind]
axiom SrcOver_right_transparent :
  forall c : Color, SrcOver Transparent c = c
@[grind]
axiom SrcOver_associative :
  forall c₁ c₂ c₃ : Color, SrcOver (SrcOver c₁ c₂) c₃ = SrcOver c₁ (SrcOver c₂ c₃)
axiom SrcOver_luminance_white:
  forall c (f: Color -> Color), f (1.0, 1.0, 1.0, 1.0) = (0.0, 0.0, 0.0, 1.0) -> f (SrcOver c (1.0, 1.0, 1.0, 1.0)) = SrcOver (f c) (0.0, 0.0, 0.0, 1.0)

axiom DstIn: BlendMode
@[grind]
axiom DstIn_left_transparent:
  forall c : Color, DstIn Transparent c = Transparent
@[grind]
axiom DstIn_right_transparent:
  forall c : Color, DstIn c Transparent = Transparent
@[grind]
axiom DstIn_right_opaque:
  forall c1 c2 : Color, isOpaque c2 -> DstIn c1 c2 = c1

-- blend mode src:
axiom Src : BlendMode
@[grind]
axiom Src_def :
  forall c₁ c₂ : Color, Src c₁ c₂ = c₂

-- PaintBlend defines how 2 layers are blended together
abbrev PaintBlend := (Float × BlendMode × ColorFilter)

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
noncomputable def blend  (l₁ l₂ : Layer) (pb: PaintBlend) : Layer :=
  let (α, bm, cf) := pb
  fun pt => bm (l₁ pt) (applyAlpha α (cf (l₂ pt)))

  -- rasterizes a geometry into a layer
@[grind]
noncomputable def raster (shape: Geometry) (paint: PaintDraw) (t: Transform) (clip: Geometry): Layer :=
  let (style, color) := paint
  fun pt =>
  let pt := (t pt)
  if (style shape) pt && (clip pt) then color pt else Transparent

-- Now we define layers
-- Empty()
@[grind]
def EmptyLayer : Layer := (fun _ => Transparent)

-- SaveLayer blends a layer onto another layer
-- l₁ bottom layer
-- l₂ top layer
@[grind]
noncomputable def SaveLayer (l₁ l₂ : Layer) (pb : PaintBlend) : Layer :=
  blend l₁ l₂ pb

theorem empty_SrcOver_SaveLayer_is_Empty l:
  SaveLayer l EmptyLayer (1.0, SrcOver, idColorFilter) = l :=
  by grind


-- now we define draw
@[grind]
noncomputable def Draw (l : Layer) (g : Geometry) (pd : PaintDraw) (pb : PaintBlend) (t: Transform)(clip : Geometry): Layer :=
  blend l (raster g pd t clip) pb

theorem lone_draw_inside_opaque_srcover_savelayer
  (bottom : Layer) (g : Geometry) (pd : PaintDraw) (α: Float) (c : Geometry) (t: Transform) cf:
  SaveLayer bottom (Draw EmptyLayer g pd (α, SrcOver, cf) t c) (1.0, SrcOver, idColorFilter) = Draw bottom g pd (α, SrcOver, cf) t c :=
  by grind


theorem lone_softlight_draw_inside_opaque_srcover_savelayer
  (g : Geometry) (pd : PaintDraw) (α: Float) (c : Geometry) (t: Transform) (any_bm: BlendMode) cf:
  SaveLayer EmptyLayer (Draw EmptyLayer g pd (α, any_bm, cf) t c) (1.0, SrcOver, id) = Draw EmptyLayer g pd (α, any_bm, cf) t c :=
  by grind

theorem empty_src_is_noop g pd t c:
  Draw EmptyLayer g pd (0.0, Src, id) t c = EmptyLayer := by
  grind

theorem last_draw_inside_opaque_srcover_savelayer
  (l₁ l₂ : Layer) (g c : Geometry) (pd : PaintDraw) (α : Float) (t : Transform) cf:
  SaveLayer l₁ (Draw l₂ g pd (α, SrcOver, cf) t c) (1.0, SrcOver, id) = Draw (SaveLayer l₁ l₂ (1.0, SrcOver, id)) g pd (α, SrcOver, cf) t c := by
  grind

theorem dstin_into_clip g1 pd1 a1 c1 t g2 c2 c (H: isOpaque c):
  SaveLayer (Draw EmptyLayer g1 pd1 (a1, SrcOver, id) t c1)
  (Draw EmptyLayer g2 (Fill, fun _ => c) (1.0, SrcOver, id) t c2) (1.0, DstIn, id)
  =
  Draw EmptyLayer g1 pd1 (a1, SrcOver, id) t (intersect c1 (intersect g2 c2)) := by
  simp [SaveLayer, Draw, blend]
  ext pt
  simp [raster, EmptyLayer, intersect]
  cases (c1 (t pt))
  · grind
  · simp [applyAlpha_opaque]
    cases (c2 (t pt))
    · grind
    · simp [SrcOver_right_transparent]
      simp [Fill]
      cases (pd1.fst g1 (t pt))
      · simp [applyAlpha_on_transparent]
        simp [DstIn_left_transparent]
      · let b := g2 (t pt)
        cases b
        · grind
        · grind

theorem subsume_colorfilter g style c transform clip f (H: f Transparent = Transparent):
  SaveLayer EmptyLayer (Draw EmptyLayer g (style, fun _ => c) (1.0, SrcOver, id) transform clip)
                       (1.0, SrcOver, f) =
  Draw EmptyLayer g (style, fun _ => f c) (1.0, SrcOver, id) transform clip := by grind

theorem subsume_colorfilter1 g style c transform clip f l (H: f Transparent = Transparent):
  SaveLayer l (Draw EmptyLayer g (style, fun _ => c) (1.0, SrcOver, id) transform clip)
                       (1.0, SrcOver, f) =
  Draw l g (style, fun _ => f c) (1.0, SrcOver, id) transform clip := by grind

theorem subsume_luminance_white g style transform clip f l1 l2
    (H2 : f (1.0, 1.0, 1.0, 1.0) = (0.0, 0.0, 0.0, 1.0)):
  SaveLayer l1 (Draw l2 g (style, fun _ => (1.0, 1.0, 1.0, 1.0)) (1.0, SrcOver, id) transform clip)
                       (1.0, SrcOver, f) =
  Draw (SaveLayer l1 l2 (1.0, SrcOver, f)) g (style, fun _ => f (1.0, 1.0, 1.0, 1.0)) (1.0, SrcOver, id) transform clip := by
  simp [SaveLayer, Draw, blend, raster, applyAlpha_opaque, SrcOver_associative]
  ext pt
  cases style g (transform pt) <;> simp
  · simp [SrcOver_left_transparent]
  · cases clip (transform pt) <;> simp
    · simp [SrcOver_left_transparent]
    · simp [H2]
      have H3 := SrcOver_luminance_white (l2 pt) f H2
      simp [H3]

theorem subsume_luminance_black g style transform clip f l1 l2
    (H2 : f (0.0, 0.0, 0.0, 1.0) = Transparent):
  SaveLayer l1 (Draw l2 g (style, fun _ => (0.0, 0.0, 0.0, 1.0)) (1.0, SrcOver, id) transform clip)
                       (1.0, SrcOver, f) =
  Draw (SaveLayer l1 l2 (1.0, SrcOver, f)) g (style, fun _ => f (0.0, 0.0, 0.0, 1.0)) (0.0, SrcOver, id) transform clip := by
  simp [SaveLayer, Draw, blend, raster, applyAlpha_opaque, SrcOver_associative]
  ext pt
  cases style g (transform pt) <;> simp
  · simp [applyAlpha_on_transparent, SrcOver_left_transparent]
  · cases clip (transform pt) <;> simp
    · simp [applyAlpha_on_transparent, SrcOver_left_transparent]
    · simp [H2, applyAlpha_transparent]
