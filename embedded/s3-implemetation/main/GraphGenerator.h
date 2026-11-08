/*
 * GraphGenerator.h
 * Graph generation and curve plotting for thermal printer
 *
 * Migration note:
 *  - pgm_read_word()/PROGMEM removed: flash arrays are directly
 *    dereferenceable on ESP32-S3 (see readSample()).
 *  - Serial.println() diagnostics replaced with ESP_LOG in the .cpp.
 */

#ifndef GRAPH_GENERATOR_H
#define GRAPH_GENERATOR_H

#include <cstdint>
#include <cstring>
#include <cstdlib>

#include "BitmapCanvas.h"

class GraphGenerator
{
private:
  BitmapCanvas *canvas;
  uint16_t width;
  uint16_t height;
  uint16_t leftMargin;
  uint16_t topMargin;

  uint16_t xMax;
  uint16_t xStep;
  uint16_t yMax;
  uint16_t yStep;

  uint16_t gridXSpacing;
  uint16_t gridYSpacing;

  uint16_t graphWidth;
  uint16_t graphStartX;
  uint16_t graphStartY;

  static inline int16_t readSample(const int16_t *data, uint16_t idx)
  {
    // Flash is memory-mapped on ESP32-S3 — direct dereference works for
    // both flash-resident and RAM-resident sources.
    return data[idx];
  }

  void applyMovingAverage(int16_t *data, uint16_t dataLen, uint8_t window = 5);

public:
  GraphGenerator(BitmapCanvas *cnv, uint16_t w, uint16_t h,
                 uint16_t lm, uint16_t tm,
                 uint16_t xmax, uint16_t xstp,
                 uint16_t ymax, uint16_t ystp,
                 uint16_t gridX, uint16_t gridY)
      : canvas(cnv), width(w), height(h),
        leftMargin(lm), topMargin(tm),
        xMax(xmax), xStep(xstp),
        yMax(ymax), yStep(ystp),
        gridXSpacing(gridX), gridYSpacing(gridY)
  {
    graphWidth = gridYSpacing * (yMax / yStep);
    graphStartX = leftMargin;
    graphStartY = topMargin;
  }

  void drawYAxisLabels();
  void drawGrid(bool dashed = true);
  void drawXAxisLabels();
  void drawCurve(const int16_t *rawData, uint16_t dataLen, uint8_t thickness = 1);
};

#endif // GRAPH_GENERATOR_H
