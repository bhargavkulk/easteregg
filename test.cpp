#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkPaint.h"
#include "include/core/SkSurface.h"

void draw_000_simpleDraw(SkCanvas *canvas) {
  SkPaint paint;
  paint.setColor(SK_ColorRED);
  canvas->drawRect(SkRect::MakeLTRB(20, 20, 100, 100), paint);
}
