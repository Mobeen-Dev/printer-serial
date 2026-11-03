/*
 * ThermalPrinter.h
 * ESC/POS compatible thermal printer control for ESP32-S3
 * Compatible with Epson TM-T88III
 *
 * Migration note:
 *  - HardwareSerial& replaced with a uart_port_t (the ESP-IDF UART driver
 *    must already be installed/configured by the caller via
 *    uart_driver_install() + uart_param_config() + uart_set_pin() before
 *    constructing this class — see esp32_thermal_printer.cpp).
 */

#ifndef THERMAL_PRINTER_H
#define THERMAL_PRINTER_H

#include <cstdint>
#include <cstddef>
#include "driver/uart.h"

// ESC/POS Command bytes
#define ESC 0x1B
#define GS 0x1D

// Alignment options
enum PrintAlign
{
  ALIGN_LEFT = 0,
  ALIGN_CENTER = 1,
  ALIGN_RIGHT = 2
};

class ThermalPrinter
{
private:
  uart_port_t _uart_port;

  size_t writeBytes(const uint8_t *buf, size_t len, bool log = true);
  bool sendCommand(const uint8_t *cmd, size_t len, uint16_t delayMs = 50);
  bool sendByte(uint8_t byte, uint16_t delayMs = 10);

public:
  explicit ThermalPrinter(uart_port_t port) : _uart_port(port) {}

  bool begin();
  void setDefault();
  void setDensity(uint8_t density = 8, uint8_t breakTime = 2);
  void cancelPrintData(uint8_t count = 4);
  void setLineHeight(uint8_t val = 32);
  void println(const char *text = "");
  void setAlign(PrintAlign align);
  void setFontSize(uint8_t width = 1, uint8_t height = 1);
  bool printBitmap(uint16_t width, uint16_t height, const uint8_t *bitmapData);
  void feed(uint8_t lines = 1);
  void cut();
};

#endif // THERMAL_PRINTER_H
