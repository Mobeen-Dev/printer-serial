/*
 * BitmapCanvas.h
 * Bitmap graphics canvas for thermal printer
 * Supports pixel drawing, lines, and text rendering
 */

#ifndef BITMAP_CANVAS_H
#define BITMAP_CANVAS_H

#include <Arduino.h>
#include "Font5x7.h"

class BitmapCanvas {
private:
  uint16_t width;
  uint16_t height;
  uint16_t bytesPerLine;
  uint8_t* data;
  
public:
  BitmapCanvas(uint16_t w, uint16_t h) : width(w), height(h) {
    bytesPerLine = width / 8;
    size_t totalBytes = bytesPerLine * height;
    
    Serial.printf("  Allocating %d bytes for canvas...\n", totalBytes);
    data = (uint8_t*)malloc(totalBytes);
    
    if (!data) {
      Serial.println("  ✗ Canvas allocation failed!");
      width = 0;
      height = 0;
      bytesPerLine = 0;
    } else {
      Serial.println("  ✓ Canvas allocated");
    }
  }
  
  ~BitmapCanvas() {
    if (data) {
      free(data);
      data = nullptr;
    }
  }
  
  // Clear canvas to white
  void clear() {
    if (data) {
      memset(data, 0, bytesPerLine * height);
    }
  }
  
  // Set a single pixel (black)
  void setPixel(int16_t x, int16_t y) {
    if (!data || x < 0 || x >= width || y < 0 || y >= height) {
      return;
    }
    
    uint32_t byteIndex = (x / 8) + y * bytesPerLine;
    uint8_t bitPosition = x & 7;
    data[byteIndex] |= (0x80 >> bitPosition);
  }
  
  // Draw vertical line
  void drawVerticalLine(int16_t x, int16_t y_start = 0, int16_t y_end = -1, bool dashed = false) {
    if (y_end == -1) y_end = height;
    
    for (int16_t y = y_start; y < y_end; y++) {
      if (!dashed || (y / 4) % 2 == 0) {
        setPixel(x, y);
      }
    }
  }
  
  // Draw horizontal line
  void drawHorizontalLine(int16_t y, int16_t x_start = 0, int16_t x_end = -1, bool dashed = false) {
    if (x_end == -1) x_end = width;
    
    for (int16_t x = x_start; x < x_end; x++) {
      if (!dashed || (x / 4) % 2 == 0) {
        setPixel(x, y);
      }
    }
  }
  
  // Draw character from font
  void drawChar(char c, int16_t x, int16_t y, uint8_t size = 1, bool rotate90 = false) {
    if (!data) return;
    
    const uint8_t* glyph = getFont5x7Char(c);
    if (!glyph) return;
    
    if (rotate90) {
      // Rotate 90° clockwise
      for (uint8_t row = 0; row < 7; row++) {
        uint8_t line = glyph[row];
        for (uint8_t col = 0; col < 5; col++) {
          if (line & (0x80 >> col)) {
            int16_t px = x + (6 - row) * size;
            int16_t py = y + col * size;
            
            for (uint8_t sy = 0; sy < size; sy++) {
              for (uint8_t sx = 0; sx < size; sx++) {
                setPixel(px + sx, py + sy);
              }
            }
          }
        }
      }
    } else {
      // Normal orientation
      for (uint8_t row = 0; row < 7; row++) {
        uint8_t line = glyph[row];
        for (uint8_t col = 0; col < 5; col++) {
          if (line & (0x80 >> col)) {
            int16_t px = x + col * size;
            int16_t py = y + row * size;
            
            for (uint8_t sy = 0; sy < size; sy++) {
              for (uint8_t sx = 0; sx < size; sx++) {
                setPixel(px + sx, py + sy);
              }
            }
          }
        }
      }
    }
  }
  
  // Draw text string
  void drawText(const char* text, int16_t x, int16_t y, uint8_t size = 1, bool rotate90 = false) {
    int16_t offset = 0;
    
    while (*text) {
      drawChar(*text, x, y + offset, size, rotate90);
      
      if (rotate90) {
        offset += 8 * size;  // Character height when rotated
      } else {
        offset += 6 * size;  // Character width + spacing
      }
      
      text++;
    }
  }
  
  // Draw thick line using Bresenham's algorithm
  void drawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t thickness = 1) {
    int16_t dx = abs(x1 - x0);
    int16_t dy = -abs(y1 - y0);
    int16_t sx = (x0 < x1) ? 1 : -1;
    int16_t sy = (y0 < y1) ? 1 : -1;
    int16_t err = dx + dy;
    
    while (true) {
      // Draw thick point
      int16_t halfThick = thickness / 2;
      for (int16_t ty = -halfThick; ty <= halfThick; ty++) {
        for (int16_t tx = -halfThick; tx <= halfThick; tx++) {
          setPixel(x0 + tx, y0 + ty);
        }
      }
      
      if (x0 == x1 && y0 == y1) break;
      
      int16_t e2 = 2 * err;
      if (e2 >= dy) {
        err += dy;
        x0 += sx;
      }
      if (e2 <= dx) {
        err += dx;
        y0 += sy;
      }
    }
  }
  
  // Getters
  uint16_t getWidth() const { return width; }
  uint16_t getHeight() const { return height; }
  const uint8_t* getData() const { return data; }
  bool isValid() const { return data != nullptr; }
};

#endif // BITMAP_CANVAS_H
