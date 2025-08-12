import Mathlib.Data.Real.Basic
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

def Interval (lo hi : ℝ) := { x : ℝ // lo ≤ x ∧ x ≤ hi }

notation "⟦" lo ", " hi "⟧" => Interval lo hi

-- premultiplied argb colors
structure Color where
  a : ⟦0, 1⟧
  r : ⟦0, a.val⟧
  g : ⟦0, a.val⟧
  b : ⟦0, a.val⟧

-- Simple semi-transparent white
noncomputable def Color.transparent : Color := {
  a := ⟨0, by norm_num, by norm_num⟩,
  r := ⟨0, by norm_num, by norm_num⟩,
  g := ⟨0, by norm_num, by norm_num⟩,
  b := ⟨0, by norm_num, by norm_num⟩
}

theorem srcover_alpha (src_a dst_a : Interval 0 1) :
  0 ≤ src_a.val + dst_a.val * (1 - src_a.val) ∧
  src_a.val + dst_a.val * (1 - src_a.val) ≤ 1 := by
  constructor
  · -- Lower bound: 0 ≤ src_a + dst_a * (1 - src_a)
    have h1 : 0 ≤ src_a.val := src_a.2.1
    have h2 : 0 ≤ dst_a.val := dst_a.2.1
    have h3 : src_a.val ≤ 1 := src_a.2.2
    have h4 : 0 ≤ 1 - src_a.val := by linarith [h3]
    have h5 : 0 ≤ dst_a.val * (1 - src_a.val) := by apply mul_nonneg h2 h4
    linarith [h1, h5]
  · -- Upper bound: src_a + dst_a * (1 - src_a) ≤ 1
    have h1 : src_a.val ≤ 1 := src_a.2.2
    have h2 : dst_a.val ≤ 1 := dst_a.2.2
    have h3 : 0 ≤ 1 - src_a.val := by linarith [h1]
    have h4 : dst_a.val * (1 - src_a.val) ≤ 1 * (1 - src_a.val) := by
      apply mul_le_mul_of_nonneg_right h2 h3
    have h5 : 1 * (1 - src_a.val) = 1 - src_a.val := by ring
    rw [h5] at h4
    linarith [h1, h4]

theorem srcover_color
  (src_a dst_a : Interval 0 1) (src_c : Interval 0 src_a.val) (dst_c : Interval 0 dst_a.val) :
  0 ≤ src_c.val + dst_c.val * (1 - src_a.val) ∧
  src_c.val + dst_c.val * (1 - src_a.val) ≤ src_a.val + dst_a.val * (1 - src_a.val) := by
  constructor
  · -- Lower bound: 0 ≤ src_c + dst_c * (1 - src_a)
    have h1 : 0 ≤ src_c.val := src_c.2.1
    have h2 : 0 ≤ dst_c.val := dst_c.2.1
    have h3 : 0 ≤ 1 - src_a.val := by linarith [src_a.2.2]
    have h4 : 0 ≤ dst_c.val * (1 - src_a.val) := by apply mul_nonneg h2 h3
    linarith [h1, h4]
  · -- Upper bound: src_c + dst_c * (1 - src_a) ≤ blended alpha
    have h1 : src_c.val ≤ src_a.val := src_c.2.2
    have h2 : dst_c.val ≤ dst_a.val := dst_c.2.2
    have h3 : 0 ≤ 1 - src_a.val := by linarith [src_a.2.2]
    have h4 : dst_c.val * (1 - src_a.val) ≤ dst_a.val * (1 - src_a.val) := by
      apply mul_le_mul_of_nonneg_right h2 h3
    linarith [h1, h4]

-- Source over blending operation
noncomputable def src_over (src dst : Color) : Color := {
  a := ⟨src.a.val + dst.a.val * (1 - src.a.val), srcover_alpha src.a dst.a⟩,
  r := ⟨src.r.val + dst.r.val * (1 - src.a.val), srcover_color src.a dst.a src.r dst.r⟩,
  g := ⟨src.g.val + dst.g.val * (1 - src.a.val), srcover_color src.a dst.a src.g dst.g⟩,
  b := ⟨src.b.val + dst.b.val * (1 - src.a.val), srcover_color src.a dst.a src.b dst.b⟩
}

theorem src_over.left_transparent c :
  src_over Color.transparent c = c := by
  simp [src_over, Color.transparent]
  cases c with
  | mk a r g b =>
    simp
    constructor
    · rw [Subtype.heq_iff_coe_eq]
      simp
    · constructor
      · rw [Subtype.heq_iff_coe_eq]
        simp
      · rw [Subtype.heq_iff_coe_eq]
        simp

theorem src_over.right_transparent c :
  src_over c Color.transparent = c := by
  simp [src_over, Color.transparent]
  cases c with
  | mk a r g b =>
    simp
    constructor
    · rw [Subtype.heq_iff_coe_eq]
      simp
    · constructor
      · rw [Subtype.heq_iff_coe_eq]
        simp
      · rw [Subtype.heq_iff_coe_eq]
        simp

theorem src_over.associative p q r :
  src_over (src_over p q) r = src_over p (src_over q r) := by
  simp [src_over]
  constructor
  · ring_nf
  · constructor
    · rw [Subtype.heq_iff_coe_eq] <;> grind
    · constructor
      · rw [Subtype.heq_iff_coe_eq] <;> grind
      · rw [Subtype.heq_iff_coe_eq] <;> grind
