import LambdaSkiaProofs.LambdaSkia

inductive Clips where
  | Empty : Clips
  | Single : Geometry → Clips
  | And : Clips → Clips → Clips
  | Or : Clips → Clips → Clips

def toGeometry : Clips → Geometry
  | Clips.Empty => fun _ => false
  | Clips.Single g => g
  | Clips.And c1 c2 => intersect (toGeometry c1) (toGeometry c2)
  | Clips.Or c1 c2 => fun pt => (toGeometry c1 pt) || (toGeometry c2 pt)
