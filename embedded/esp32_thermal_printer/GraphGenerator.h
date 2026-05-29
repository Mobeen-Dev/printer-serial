/*
 * GraphGenerator.h
 * Graph generation and curve plotting for thermal printer
 *
 * Refactor note:
 *  - Data sourcing is now external (DataSource HAL)
 *  - Curve pipeline uses int16_t (0..Y_MAX) and supports PROGMEM-backed sources
 */

#ifndef GRAPH_GENERATOR_H
#define GRAPH_GENERATOR_H

#include <Arduino.h>
#include <pgmspace.h>

#include "BitmapCanvas.h"

class GraphGenerator {
private:
  BitmapCanvas* canvas;
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

  static inline int16_t readSample(const int16_t* data, uint16_t idx) {
    // PROGMEM-safe read (also works for RAM on ESP32)
    return (int16_t)pgm_read_word(&data[idx]);
  }

  // Moving average filter
  // Smoothing kept for future live UART data which may be noisy
  void applyMovingAverage(int16_t* data, uint16_t dataLen, uint8_t window = 5) {
    if (window < 2 || !data || dataLen == 0) return;

    int16_t* temp = (int16_t*)malloc(dataLen * sizeof(int16_t));
    if (!temp) return;

    int16_t half = window / 2;

    for (uint16_t i = 0; i < dataLen; i++) {
      int32_t sum = 0;
      uint16_t count = 0;

      for (int16_t j = (int16_t)i - half; j <= (int16_t)i + half; j++) {
        if (j >= 0 && j < (int16_t)dataLen) {
          sum += data[(uint16_t)j];
          count++;
        }
      }

      temp[i] = (count > 0) ? (int16_t)(sum / (int32_t)count) : data[i];
    }

    memcpy(data, temp, dataLen * sizeof(int16_t));
    free(temp);
  }

public:
  GraphGenerator(BitmapCanvas* cnv, uint16_t w, uint16_t h,
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
  
  // Draw Y-axis labels (Pressure - horizontal across top)
  void drawYAxisLabels() {
    uint16_t numYDiv = yMax / yStep;
    
    for (uint16_t i = 0; i <= numYDiv; i++) {
      int16_t xPos = graphStartX + i * gridYSpacing;
      uint16_t value = i * yStep;
      
      if (value > 0) {
        char label[8];
        sprintf(label, "%dK", value);
        canvas->drawText(label, xPos - 13, 5, 2, true);  // Rotated 90°
      }
    }
  }
  
  // Draw grid lines
  void drawGrid(bool dashed = true) {
    // Horizontal grid lines (time divisions)
    uint16_t numXDiv = xMax / xStep;
    for (uint16_t i = 0; i <= numXDiv; i++) {
      int16_t yPos = graphStartY + i * gridXSpacing;
      if (yPos <= height + topMargin) {
        canvas->drawHorizontalLine(yPos, graphStartX, graphStartX + graphWidth, dashed);
      }
    }
    
    // Vertical grid lines (pressure divisions)
    uint16_t numYDiv = yMax / yStep;
    for (uint16_t i = 0; i <= numYDiv; i++) {
      int16_t xPos = graphStartX + i * gridYSpacing;
      canvas->drawVerticalLine(xPos, graphStartY, height + topMargin, dashed);
    }
  }
  
  // Draw X-axis labels (Time - vertical along left side)
  void drawXAxisLabels() {
    uint16_t numXDiv = xMax / xStep;

    // "TIME" at axis origin — unit context for X-axis (time), standard graph placement
    // Pseudo-bold: draw twice with a 1px offset
    canvas->drawText("TIME", 2, graphStartY - 70, 2, true);
    canvas->drawText("TIME", 3, graphStartY - 70, 2, true);
    // "sec" size 3 — unit label, intentionally larger than numeric labels for readability
    // canvas->drawText("sec", 2, graphStartY - 18, 3, true);

    for (uint16_t i = 0; i <= numXDiv; i++) {
      int16_t yPos = graphStartY + i * gridXSpacing;
      uint16_t value = i * xStep;
      
      const int16_t labelHeight = 14;  // 7px font height × size 2
      int16_t labelY = yPos - 3;
      const int16_t maxLabelY = (int16_t)canvas->getHeight() - labelHeight;
      // Guard: ensure label (14px tall at size=2) does not overflow canvas bottom
      if (labelY > maxLabelY) {
        labelY = maxLabelY;
      }
      if (labelY < 0) {
        labelY = 0;
      }

      char label[4];
      sprintf(label, "%d", value);
      canvas->drawText(label, 10, labelY, 2, true);  // Rotated 90°
    }
  }

  // REMOVED: drawBottomLabel() — TIME label moved to axis origin (see drawXAxisLabels)
  
  // Draw curve on canvas
  void drawCurve(const int16_t* rawData, uint16_t dataLen, uint8_t thickness = 1) {
    if (!canvas || !canvas->isValid()) {
      Serial.println("  ✗ Canvas invalid!");
      return;
    }

    if (!rawData) {
      Serial.println("  ✗ Curve data pointer is null!");
      return;
    }

    if (dataLen == 0) {
      Serial.println("  ✗ Curve data length is 0!");
      return;
    }

    // Graph plotting height is the graph area height (not including margins)
    const uint16_t graphHeight = height;

    // Downsample to graph height using max pooling
    int16_t* processedData = (int16_t*)malloc(graphHeight * sizeof(int16_t));
    if (!processedData) {
      Serial.println("  ✗ Failed to allocate processed data!");
      return;
    }

    if (dataLen >= graphHeight) {
      // Pool window ratio auto-computed from dataLen / graphHeight
      // Currently ~1.10 (750 points / ~680 pixel rows)
      // Will increase automatically as data point count grows with real IC data
      const float ratio = (float)dataLen / (float)graphHeight;

      for (uint16_t i = 0; i < graphHeight; i++) {
        const uint16_t start = (uint16_t)(i * ratio);
        const uint16_t end = (uint16_t)((i + 1) * ratio);

        int16_t maxVal = 0;
        for (uint16_t j = start; j < end && j < dataLen; j++) {
          int16_t v = readSample(rawData, j);
          v = (int16_t)constrain(v, 0, (int16_t)yMax);
          if (v > maxVal) {
            maxVal = v;
          }
        }

        processedData[i] = maxVal;
      }
    } else {
      // Copy and pad if needed
      for (uint16_t i = 0; i < dataLen && i < graphHeight; i++) {
        int16_t v = readSample(rawData, i);
        processedData[i] = (int16_t)constrain(v, 0, (int16_t)yMax);
      }
      for (uint16_t i = dataLen; i < graphHeight; i++) {
        processedData[i] = 0;
      }
    }

    // Apply smoothing
    applyMovingAverage(processedData, graphHeight, 11);

    // Scale factor: pixels per pressure unit
    const float scale = (float)graphWidth / (float)yMax;

    // Convert to pixel coordinates and draw
    int16_t prevX = 0, prevY = 0;
    bool first = true;

    for (uint16_t y = 0; y < graphHeight; y++) {
      int16_t val = (int16_t)constrain(processedData[y], 0, (int16_t)yMax);

      // Map value to x position
      const int16_t xOffset = (int16_t)(val * scale);
      const int16_t x = (int16_t)graphStartX + xOffset;
      const int16_t yPos = (int16_t)graphStartY + (int16_t)y;

      if (!first) {
        canvas->drawLine(prevX, prevY, x, yPos, thickness);
      }

      prevX = x;
      prevY = yPos;
      first = false;
    }

    free(processedData);

    Serial.println("  ✓ Curve drawn");
  }
};

#endif // GRAPH_GENERATOR_H
