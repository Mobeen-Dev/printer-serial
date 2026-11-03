/*
 * ThermalPrinter.cpp
 * Implementation of the ESC/POS driver over the native ESP-IDF UART driver.
 */

#include "ThermalPrinter.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include <cstring>
#include <algorithm>

static const char *TAG = "ThermalPrinter";

// Set to 1 to hex-dump every transmitted byte (replaces Arduino PRINTER_DEBUG)
#define PRINTER_DEBUG 1

size_t ThermalPrinter::writeBytes(const uint8_t *buf, size_t len, bool log)
{
#if PRINTER_DEBUG
  if (log)
  {
    // Build and emit a single log line instead of many small prints —
    // cheaper on a UART-backed log sink than printf-per-byte.
    char hexbuf[3 * 32 + 1];
    size_t pos = 0;
    size_t n = std::min(len, (size_t)32);
    for (size_t i = 0; i < n && pos + 3 < sizeof(hexbuf); i++)
    {
      pos += snprintf(hexbuf + pos, sizeof(hexbuf) - pos, "%02X ", buf[i]);
    }
    ESP_LOGD(TAG, "TX (%u bytes): %s%s", (unsigned)len, hexbuf, (len > 32) ? "..." : "");
  }
#endif
  int written = uart_write_bytes(_uart_port, (const char *)buf, len);
  return (written < 0) ? 0 : (size_t)written;
}

bool ThermalPrinter::sendCommand(const uint8_t *cmd, size_t len, uint16_t delayMs)
{
  size_t written = writeBytes(cmd, len);
  uart_wait_tx_done(_uart_port, pdMS_TO_TICKS(1000));
  vTaskDelay(pdMS_TO_TICKS(delayMs));
  return (written == len);
}

bool ThermalPrinter::sendByte(uint8_t byte, uint16_t delayMs)
{
  writeBytes(&byte, 1);
  uart_wait_tx_done(_uart_port, pdMS_TO_TICKS(1000));
  vTaskDelay(pdMS_TO_TICKS(delayMs));
  return true;
}

bool ThermalPrinter::begin()
{
  // Clear any stale RX bytes
  uart_flush_input(_uart_port);

  vTaskDelay(pdMS_TO_TICKS(500));

  // Initialize: ESC @
  uint8_t init[] = {ESC, '@'};
  if (!sendCommand(init, 2, 500))
  {
    return false;
  }

  vTaskDelay(pdMS_TO_TICKS(200));

  setDefault();
  return true;
}

void ThermalPrinter::setDefault()
{
  uint8_t cmd[] = {ESC, '@'};
  sendCommand(cmd, 2, 300);
}

void ThermalPrinter::setDensity(uint8_t density, uint8_t breakTime)
{
  // TM-T88III does not support ESC 7; no-op (matches original).
  (void)density;
  (void)breakTime;
}

void ThermalPrinter::cancelPrintData(uint8_t count)
{
  for (uint8_t i = 0; i < count; i++)
  {
    sendByte(0x18, 5); // CAN
  }
}

void ThermalPrinter::setLineHeight(uint8_t val)
{
  if (val < 24)
    val = 24;
  uint8_t cmd[] = {ESC, '3', val};
  sendCommand(cmd, 3, 10);
}

void ThermalPrinter::println(const char *text)
{
  if (text && text[0] != '\0')
  {
    writeBytes(reinterpret_cast<const uint8_t *>(text), strlen(text));
  }
  uint8_t newline = '\n';
  writeBytes(&newline, 1);
  uart_wait_tx_done(_uart_port, pdMS_TO_TICKS(1000));
  vTaskDelay(pdMS_TO_TICKS(10));
}

void ThermalPrinter::setAlign(PrintAlign align)
{
  uint8_t cmd[] = {ESC, 'a', (uint8_t)align};
  sendCommand(cmd, 3, 50);
}

void ThermalPrinter::setFontSize(uint8_t width, uint8_t height)
{
  if (width < 1)
    width = 1;
  if (width > 8)
    width = 8;
  if (height < 1)
    height = 1;
  if (height > 8)
    height = 8;

  uint8_t size = ((width - 1) << 4) | (height - 1);
  uint8_t cmd[] = {GS, '!', size};
  sendCommand(cmd, 3, 50);
}

bool ThermalPrinter::printBitmap(uint16_t width, uint16_t height, const uint8_t *bitmapData)
{
  uint16_t widthBytes = width / 8;

  // GS v 0 - Print raster bitmap
  uint8_t cmd[] = {
      GS, 'v', '0',
      0x00, // Normal mode
      (uint8_t)(widthBytes & 0xFF),
      (uint8_t)((widthBytes >> 8) & 0xFF),
      (uint8_t)(height & 0xFF),
      (uint8_t)((height >> 8) & 0xFF)};

  if (!sendCommand(cmd, 8, 20))
  {
    return false;
  }

  // Send bitmap data in chunks
  const size_t CHUNK_SIZE = 512;
  size_t totalBytes = (size_t)widthBytes * height;
  size_t sent = 0;

  while (sent < totalBytes)
  {
    size_t chunkSize = std::min(CHUNK_SIZE, totalBytes - sent);
    size_t written = writeBytes(bitmapData + sent, chunkSize, false);

    if (written != chunkSize)
    {
      ESP_LOGW(TAG, "Warning: Sent %u of %u bytes", (unsigned)written, (unsigned)chunkSize);
    }

    sent += written;
    uart_wait_tx_done(_uart_port, pdMS_TO_TICKS(1000));

    if (sent % 4096 == 0)
    {
      ESP_LOGI(TAG, "  Progress: %u%%", (unsigned)((sent * 100) / totalBytes));
    }

    vTaskDelay(pdMS_TO_TICKS(10));
  }

  vTaskDelay(pdMS_TO_TICKS(50));
  return true;
}

void ThermalPrinter::feed(uint8_t lines)
{
  uint8_t cmd[] = {ESC, 'd', lines};
  sendCommand(cmd, 3, lines * 50);
}

void ThermalPrinter::cut()
{
  uint8_t cmd[] = {GS, 'V', 0x00};
  sendCommand(cmd, 3, 500);
}
