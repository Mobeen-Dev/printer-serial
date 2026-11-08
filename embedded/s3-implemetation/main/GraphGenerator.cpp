/*
 * GraphGenerator.cpp
 * Implementation of axis/grid/curve drawing.
 */

#include "GraphGenerator.h"

#include "esp_heap_caps.h"
#include "esp_log.h"
#include <algorithm>

static const char *TAG = "GraphGenerator";

void GraphGenerator::applyMovingAverage(int16_t *data, uint16_t dataLen, uint8_t window)
{
  if (window < 2 || !data || dataLen == 0)
    return;

  int16_t *temp = (int16_t *)heap_caps_malloc(dataLen * sizeof(int16_t), MALLOC_CAP_8BIT);
  if (!temp)
    return;

  int16_t half = window / 2;

  for (uint16_t i = 0; i < dataLen; i++)
  {
    int32_t sum = 0;
    uint16_t count = 0;

    for (int16_t j = (int16_t)i - half; j <= (int16_t)i + half; j++)
    {
      if (j >= 0 && j < (int16_t)dataLen)
      {
        sum += data[(uint16_t)j];
        count++;
      }
    }

    temp[i] = (count > 0) ? (int16_t)(sum / (int32_t)count) : data[i];
  }

  memcpy(data, temp, dataLen * sizeof(int16_t));
  heap_caps_free(temp);
}

void GraphGenerator::drawYAxisLabels()
{
  const uint16_t numYDiv = yMax / yStep;
  const uint16_t valueIncrement = yStep;

  int16_t xPos = graphStartX;
  uint16_t value = valueIncrement;

  char label[16];

  for (uint16_t i = 1; i <= numYDiv; ++i)
  {
    snprintf(label, sizeof(label), "%u", (unsigned)value);

    canvas->drawText(
        label,
        xPos + gridYSpacing - 13,
        5,
        2,
        true);

    xPos += gridYSpacing;
    value += valueIncrement;
  }
}

void GraphGenerator::drawGrid(bool dashed)
{
  // Horizontal grid lines (time divisions)
  uint16_t numXDiv = xMax / xStep;
  for (uint16_t i = 0; i <= numXDiv; i++)
  {
    int16_t yPos = graphStartY + i * gridXSpacing;
    if (yPos <= height + topMargin)
    {
      canvas->drawHorizontalLine(yPos, graphStartX, graphStartX + graphWidth, dashed);
    }
  }

  // Vertical grid lines (pressure divisions)
  uint16_t numYDiv = yMax / yStep;
  for (uint16_t i = 0; i <= numYDiv; i++)
  {
    int16_t xPos = graphStartX + i * gridYSpacing;
    canvas->drawVerticalLine(xPos, graphStartY, height + topMargin, dashed);
  }
}

void GraphGenerator::drawXAxisLabels()
{
  uint16_t numXDiv = xMax / xStep;

  // "TIME" at axis origin — pseudo-bold via 1px-offset double draw.
  canvas->drawText("TIME", 2, graphStartY - 70, 2, true);
  canvas->drawText("TIME", 3, graphStartY - 70, 2, true);

  for (uint16_t i = 0; i <= numXDiv; i++)
  {
    int16_t yPos = graphStartY + i * gridXSpacing;
    uint16_t value = i * xStep;

    const int16_t labelHeight = 14; // 7px font height × size 2
    int16_t labelY = yPos - 3;
    const int16_t maxLabelY = (int16_t)canvas->getHeight() - labelHeight;
    if (labelY > maxLabelY)
    {
      labelY = maxLabelY;
    }
    if (labelY < 0)
    {
      labelY = 0;
    }

    char label[16];
    snprintf(label, sizeof(label), "%u", (unsigned)value);
    canvas->drawText(label, 10, labelY, 2, true); // Rotated 90°
  }
}

void GraphGenerator::drawCurve(const int16_t *rawData, uint16_t dataLen, uint8_t thickness)
{
  if (!canvas || !canvas->isValid())
  {
    ESP_LOGE(TAG, "  ✗ Canvas invalid!");
    return;
  }

  if (!rawData)
  {
    ESP_LOGE(TAG, "  ✗ Curve data pointer is null!");
    return;
  }

  if (dataLen == 0)
  {
    ESP_LOGE(TAG, "  ✗ Curve data length is 0!");
    return;
  }

  const uint16_t graphHeight = height;

  int16_t *processedData = (int16_t *)heap_caps_malloc(graphHeight * sizeof(int16_t), MALLOC_CAP_8BIT);
  if (!processedData)
  {
    ESP_LOGE(TAG, "  ✗ Failed to allocate processed data!");
    return;
  }

  if (dataLen >= graphHeight)
  {
    const float ratio = (float)dataLen / (float)graphHeight;

    for (uint16_t i = 0; i < graphHeight; i++)
    {
      const uint16_t start = (uint16_t)(i * ratio);
      const uint16_t end = (uint16_t)((i + 1) * ratio);

      int16_t maxVal = 0;
      for (uint16_t j = start; j < end && j < dataLen; j++)
      {
        int16_t v = readSample(rawData, j);
        // v = v * 10; // #Remove Scale the value by 10 to match the new Y_MAX of 2000
        v = (int16_t)std::clamp((int)v, 0, (int)yMax);
        if (v > maxVal)
        {
          maxVal = v;
        }
      }

      processedData[i] = maxVal;
    }
  }
  else
  {
    for (uint16_t i = 0; i < dataLen && i < graphHeight; i++)
    {
      int16_t v = readSample(rawData, i);
      processedData[i] = (int16_t)std::clamp((int)v, 0, (int)yMax);
    }
    for (uint16_t i = dataLen; i < graphHeight; i++)
    {
      processedData[i] = 0;
    }
  }

  applyMovingAverage(processedData, graphHeight, 11);

  const float scale = (float)graphWidth / (float)yMax;

  int16_t prevX = 0, prevY = 0;
  bool first = true;

  for (uint16_t y = 0; y < graphHeight; y++)
  {
    int16_t val = (int16_t)std::clamp((int)processedData[y], 0, (int)yMax);

    const int16_t xOffset = (int16_t)(val * scale);
    const int16_t x = (int16_t)graphStartX + xOffset;
    const int16_t yPos = (int16_t)graphStartY + (int16_t)y;

    if (!first)
    {
      canvas->drawLine(prevX, prevY, x, yPos, thickness);
    }

    prevX = x;
    prevY = yPos;
    first = false;
  }

  heap_caps_free(processedData);

  ESP_LOGI(TAG, "  ✓ Curve drawn");
}
