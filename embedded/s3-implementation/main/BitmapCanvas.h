/*
 * BitmapCanvas.h
 * Bitmap graphics canvas for thermal printer
 * Supports pixel drawing, lines, and text rendering
 *
 * Migration note:
 *  - Backing buffer now allocated with heap_caps_malloc(MALLOC_CAP_8BIT)
 *    instead of Arduino malloc(). MALLOC_CAP_INTERNAL is intentionally NOT
 *    forced: the canvas can be ~58KB (512x880 / 8), and requiring internal
 *    SRAM only would risk allocation failure on S3 configs without enough
 *    free internal heap. MALLOC_CAP_8BIT allows PSRAM if present.
 */

#ifndef BITMAP_CANVAS_H
#define BITMAP_CANVAS_H

#include <cstdint>
#include <cstring>

class BitmapCanvas
{
private:
  uint16_t width;
  uint16_t height;
  uint16_t bytesPerLine;
  uint8_t *data;

public:
  BitmapCanvas(uint16_t w, uint16_t h);
  ~BitmapCanvas();

  void clear();
  void setPixel(int16_t x, int16_t y);

  void drawVerticalLine(int16_t x, int16_t y_start = 0, int16_t y_end = -1, bool dashed = false);
  void drawHorizontalLine(int16_t y, int16_t x_start = 0, int16_t x_end = -1, bool dashed = false);

  void drawChar(char c, int16_t x, int16_t y, uint8_t size = 1, bool rotate90 = false);
  void drawText(const char *text, int16_t x, int16_t y, uint8_t size = 1, bool rotate90 = false);

  void drawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t thickness = 1);

  // Getters
  uint16_t getWidth() const { return width; }
  uint16_t getHeight() const { return height; }
  const uint8_t *getData() const { return data; }
  bool isValid() const { return data != nullptr; }
};

#endif // BITMAP_CANVAS_H
