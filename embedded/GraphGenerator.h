/*
 * GraphGenerator.h
 * Graph generation and curve plotting for thermal printer
 * Generates build-up curve with configurable patterns
 */

#ifndef GRAPH_GENERATOR_H
#define GRAPH_GENERATOR_H

#include <Arduino.h>
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
  
  // Simple random number generator (LCG)
  uint32_t randSeed;
  
  float random_float(float min_val, float max_val) {
    // Linear Congruential Generator
    randSeed = (1103515245 * randSeed + 12345) & 0x7FFFFFFF;
    float r = (float)randSeed / 0x7FFFFFFF;
    return min_val + r * (max_val - min_val);
  }
  
  // Moving average filter
  void applyMovingAverage(float* data, uint16_t dataLen, uint8_t window = 5) {
    if (window < 2 || !data) return;
    
    float* temp = (float*)malloc(dataLen * sizeof(float));
    if (!temp) return;
    
    int16_t half = window / 2;
    
    for (uint16_t i = 0; i < dataLen; i++) {
      float sum = 0;
      uint16_t count = 0;
      
      for (int16_t j = i - half; j <= i + half; j++) {
        if (j >= 0 && j < dataLen) {
          sum += data[j];
          count++;
        }
      }
      
      temp[i] = sum / count;
    }
    
    memcpy(data, temp, dataLen * sizeof(float));
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
    
    // Initialize random seed
    randSeed = micros();
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
      if (yPos < height + topMargin) {
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
    
    for (uint16_t i = 0; i <= numXDiv; i++) {
      int16_t yPos = graphStartY + i * gridXSpacing;
      uint16_t value = i * xStep;
      
      if (yPos < height + topMargin - 10) {
        char label[4];
        sprintf(label, "%d", value);
        canvas->drawText(label, 10, yPos - 3, 2, true);  // Rotated 90°
      }
    }
  }
  
  // Draw bottom label
  void drawBottomLabel() {
    canvas->drawText("TIME", width / 2 - 15, height + topMargin + 5, 1, true);
  }
  
  // Generate build-up curve data
  // pattern: 1 = Quadratic, 2 = Linear with noise
  float* generateBuildUpCurve(uint16_t numPoints, uint8_t pattern = 1) {
    float* data = (float*)malloc(numPoints * sizeof(float));
    if (!data) {
      Serial.println("  ✗ Failed to allocate curve data!");
      return nullptr;
    }
    
    // Calculate rise time: 26 seconds out of 30 (86.7%)
    uint16_t risePoints = (numPoints * 26) / 30;
    
    if (pattern == 1) {
      // ═══════════════════════════════════════════════════════════
      // PATTERN 1: Quadratic build-up (smooth acceleration)
      // ═══════════════════════════════════════════════════════════
      
      for (uint16_t i = 0; i < risePoints; i++) {
        float progress = (float)i / risePoints;
        float baseValue = yMax * (progress * progress);  // Quadratic
        float noise = random_float(-3.0, 3.0);
        data[i] = constrain(baseValue + noise, 0, yMax);
      }
      
      // Sudden drop to 0
      for (uint16_t i = risePoints; i < numPoints; i++) {
        data[i] = 0;
      }
      
    } else if (pattern == 2) {
      // ═══════════════════════════════════════════════════════════
      // PATTERN 2: Linear with noise (steady rise)
      // ═══════════════════════════════════════════════════════════
      
      for (uint16_t i = 0; i < risePoints; i++) {
        float progress = (float)i / risePoints;
        float baseValue = yMax * progress;  // Linear
        float noise = random_float(-8.0, 8.0);
        data[i] = constrain(baseValue + noise, 0, yMax);
      }
      
      // Sudden drop to 0
      for (uint16_t i = risePoints; i < numPoints; i++) {
        data[i] = 0;
      }
      
    } else {
      Serial.printf("  ✗ Invalid pattern %d!\n", pattern);
      free(data);
      return nullptr;
    }
    
    Serial.printf("  ✓ Generated %d data points (Pattern %d)\n", numPoints, pattern);
    return data;
  }
  
  // Draw curve on canvas
  void drawCurve(const float* rawData, uint16_t dataLen, uint8_t thickness = 1) {
    if (!rawData || !canvas || dataLen == 0) {
      Serial.println("  ✗ Invalid curve data!");
      return;
    }
    
    uint16_t graphHeight = height - graphStartY;
    
    // Downsample to graph height using max pooling
    float* processedData = (float*)malloc(graphHeight * sizeof(float));
    if (!processedData) {
      Serial.println("  ✗ Failed to allocate processed data!");
      return;
    }
    
    if (dataLen > graphHeight) {
      float ratio = (float)dataLen / graphHeight;
      
      for (uint16_t i = 0; i < graphHeight; i++) {
        uint16_t start = (uint16_t)(i * ratio);
        uint16_t end = (uint16_t)((i + 1) * ratio);
        
        float maxVal = 0;
        for (uint16_t j = start; j < end && j < dataLen; j++) {
          if (rawData[j] > maxVal) {
            maxVal = rawData[j];
          }
        }
        processedData[i] = maxVal;
      }
    } else {
      // Copy and pad if needed
      for (uint16_t i = 0; i < dataLen && i < graphHeight; i++) {
        processedData[i] = rawData[i];
      }
      for (uint16_t i = dataLen; i < graphHeight; i++) {
        processedData[i] = 0;
      }
    }
    
    // Apply smoothing
    applyMovingAverage(processedData, graphHeight, 11);
    
    // Scale factor: pixels per pressure unit
    float scale = (float)graphWidth / yMax;
    
    // Convert to pixel coordinates and draw
    int16_t prevX = 0, prevY = 0;
    bool first = true;
    
    for (uint16_t y = 0; y < graphHeight; y++) {
      float val = constrain(processedData[y], 0, yMax);
      
      // Map value to x position
      int16_t xOffset = (int16_t)(val * scale);
      int16_t x = graphStartX + xOffset;
      int16_t yPos = graphStartY + y;
      
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
