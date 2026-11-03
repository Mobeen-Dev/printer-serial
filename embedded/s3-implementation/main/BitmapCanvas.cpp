/*
 * BitmapCanvas.cpp
 * Implementation of the monochrome frame buffer.
 */

#include "BitmapCanvas.h"
#include "Font5x7.h"

#include "esp_heap_caps.h"
#include "esp_log.h"
#include <cstdlib>

static const char *TAG = "BitmapCanvas";

BitmapCanvas::BitmapCanvas(uint16_t w, uint16_t h) : width(w), height(h)
{
  bytesPerLine = width / 8;
  size_t totalBytes = (size_t)bytesPerLine * height;

  ESP_LOGI(TAG, "  Allocating %u bytes for canvas...", (unsigned)totalBytes);

  // MALLOC_CAP_8BIT (no MALLOC_CAP_INTERNAL) — see header note.
  data = (uint8_t *)heap_caps_malloc(totalBytes, MALLOC_CAP_8BIT);

  if (!data)
  {
    ESP_LOGE(TAG, "  ✗ Canvas allocation failed!");
    width = 0;
    height = 0;
    bytesPerLine = 0;
  }
  else
  {
    ESP_LOGI(TAG, "  ✓ Canvas allocated");
  }
}

BitmapCanvas::~BitmapCanvas()
{
  if (data)
  {
    heap_caps_free(data);
    data = nullptr;
  }
}

void BitmapCanvas::clear()
{
  if (data)
  {
    memset(data, 0, (size_t)bytesPerLine * height);
  }
}

void BitmapCanvas::setPixel(int16_t x, int16_t y)
{
  if (!data || x < 0 || x >= width || y < 0 || y >= height)
  {
    return;
  }

  uint32_t byteIndex = (x / 8) + y * bytesPerLine;
  uint8_t bitPosition = x & 7;
  data[byteIndex] |= (0x80 >> bitPosition);
}

void BitmapCanvas::drawVerticalLine(int16_t x, int16_t y_start, int16_t y_end, bool dashed)
{
  if (y_end == -1)
    y_end = height;

  for (int16_t y = y_start; y < y_end; y++)
  {
    if (!dashed || (y / 4) % 2 == 0)
    {
      setPixel(x, y);
    }
  }
}

void BitmapCanvas::drawHorizontalLine(int16_t y, int16_t x_start, int16_t x_end, bool dashed)
{
  if (x_end == -1)
    x_end = width;

  for (int16_t x = x_start; x < x_end; x++)
  {
    if (!dashed || (x / 4) % 2 == 0)
    {
      setPixel(x, y);
    }
  }
}

void BitmapCanvas::drawChar(char c, int16_t x, int16_t y, uint8_t size, bool rotate90)
{
  if (!data)
    return;

  const uint8_t *glyph = getFont5x7Char(c);
  if (!glyph)
    return;

  if (rotate90)
  {
    // Rotate 90° clockwise
    for (uint8_t row = 0; row < 7; row++)
    {
      uint8_t line = glyph[row];
      for (uint8_t col = 0; col < 5; col++)
      {
        if (line & (0x80 >> col))
        {
          int16_t px = x + (6 - row) * size;
          int16_t py = y + col * size;

          for (uint8_t sy = 0; sy < size; sy++)
          {
            for (uint8_t sx = 0; sx < size; sx++)
            {
              setPixel(px + sx, py + sy);
            }
          }
        }
      }
    }
  }
  else
  {
    // Normal orientation
    for (uint8_t row = 0; row < 7; row++)
    {
      uint8_t line = glyph[row];
      for (uint8_t col = 0; col < 5; col++)
      {
        if (line & (0x80 >> col))
        {
          int16_t px = x + col * size;
          int16_t py = y + row * size;

          for (uint8_t sy = 0; sy < size; sy++)
          {
            for (uint8_t sx = 0; sx < size; sx++)
            {
              setPixel(px + sx, py + sy);
            }
          }
        }
      }
    }
  }
}

void BitmapCanvas::drawText(const char *text, int16_t x, int16_t y, uint8_t size, bool rotate90)
{
  int16_t offset = 0;

  while (*text)
  {
    drawChar(*text, x, y + offset, size, rotate90);

    if (rotate90)
    {
      offset += 8 * size; // Character height when rotated
    }
    else
    {
      offset += 6 * size; // Character width + spacing
    }

    text++;
  }
}

void BitmapCanvas::drawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t thickness)
{
  int16_t dx = abs(x1 - x0);
  int16_t dy = -abs(y1 - y0);
  int16_t sx = (x0 < x1) ? 1 : -1;
  int16_t sy = (y0 < y1) ? 1 : -1;
  int16_t err = dx + dy;

  while (true)
  {
    // Draw thick point
    int16_t halfThick = thickness / 2;
    for (int16_t ty = -halfThick; ty <= halfThick; ty++)
    {
      for (int16_t tx = -halfThick; tx <= halfThick; tx++)
      {
        setPixel(x0 + tx, y0 + ty);
      }
    }

    if (x0 == x1 && y0 == y1)
      break;

    int16_t e2 = 2 * err;
    if (e2 >= dy)
    {
      err += dy;
      x0 += sx;
    }
    if (e2 <= dx)
    {
      err += dx;
      y0 += sy;
    }
  }
}
