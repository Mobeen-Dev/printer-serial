/*
 * ThermalPrinter.h
 * ESC/POS compatible thermal printer control for ESP32-S3
 * Compatible with Epson TM-T88III
 */

#ifndef THERMAL_PRINTER_H
#define THERMAL_PRINTER_H

#include <Arduino.h>
#include <HardwareSerial.h>

// ESC/POS Command bytes
#define ESC 0x1B
#define GS  0x1D

// Alignment options
enum PrintAlign {
  ALIGN_LEFT = 0,
  ALIGN_CENTER = 1,
  ALIGN_RIGHT = 2
};

class ThermalPrinter {
private:
  HardwareSerial& serial;
  
  size_t writeBytes(const uint8_t* buf, size_t len, bool log = true) {
#ifdef PRINTER_DEBUG
    if (log) {
      Serial.print("TX: ");
      for (size_t i = 0; i < len; i++) {
        Serial.printf("%02X ", buf[i]);
      }
      Serial.println();
    }
#endif
    return serial.write(buf, len);
  }

  // Send command with timeout
  bool sendCommand(const uint8_t* cmd, size_t len, uint16_t delayMs = 50) {
    size_t written = writeBytes(cmd, len);
    serial.flush();
    delay(delayMs);
    return (written == len);
  }
  
  // Send single byte command
  bool sendByte(uint8_t byte, uint16_t delayMs = 10) {
    writeBytes(&byte, 1);
    serial.flush();
    delay(delayMs);
    return true;
  }

public:
  ThermalPrinter(HardwareSerial& ser) : serial(ser) {}
  
  // Initialize printer
  bool begin() {
    // Clear buffers
    while (serial.available()) {
      serial.read();
    }
    
    delay(500);
    
    // Initialize: ESC @
    uint8_t init[] = {ESC, '@'};
    if (!sendCommand(init, 2, 500)) {
      return false;
    }
    
    delay(200);
    
    // Set defaults
    setDefault();
    return true;
  }
  
  // Reset to default settings
  void setDefault() {
    uint8_t cmd[] = {ESC, '@'};
    sendCommand(cmd, 2, 300);
  }
  
  // Set print density (TM-T88III does not support ESC 7; no-op)
  void setDensity(uint8_t density = 8, uint8_t breakTime = 2) {
    (void)density;
    (void)breakTime;
  }
  
  // Cancel any queued print data (CAN)
  void cancelPrintData(uint8_t count = 4) {
    for (uint8_t i = 0; i < count; i++) {
      sendByte(0x18, 5);
    }
  }
  
  // Set line spacing
  void setLineHeight(uint8_t val = 32) {
    if (val < 24) val = 24;
    uint8_t cmd[] = {ESC, '3', val};
    sendCommand(cmd, 3, 10);
  }
  
  // Print text line
  void println(const char* text = "") {
    if (text && text[0] != '\0') {
      writeBytes(reinterpret_cast<const uint8_t*>(text), strlen(text));
    }
    uint8_t newline = '\n';
    writeBytes(&newline, 1);
    serial.flush();
    delay(10);
  }
  
  // Set text alignment
  void setAlign(PrintAlign align) {
    uint8_t cmd[] = {ESC, 'a', (uint8_t)align};
    sendCommand(cmd, 3, 50);
  }
  
  // Set font size (width and height: 1-8)
  void setFontSize(uint8_t width = 1, uint8_t height = 1) {
    if (width < 1) width = 1;
    if (width > 8) width = 8;
    if (height < 1) height = 1;
    if (height > 8) height = 8;
    
    uint8_t size = ((width - 1) << 4) | (height - 1);
    uint8_t cmd[] = {GS, '!', size};
    sendCommand(cmd, 3, 50);
  }
  
  // Print bitmap image
  bool printBitmap(uint16_t width, uint16_t height, const uint8_t* bitmapData) {
    uint16_t widthBytes = width / 8;
    
    // GS v 0 - Print raster bitmap
    uint8_t cmd[] = {
      GS, 'v', '0',
      0x00,  // Normal mode
      (uint8_t)(widthBytes & 0xFF),
      (uint8_t)((widthBytes >> 8) & 0xFF),
      (uint8_t)(height & 0xFF),
      (uint8_t)((height >> 8) & 0xFF)
    };
    
    if (!sendCommand(cmd, 8, 20)) {
      return false;
    }
    
    // Send bitmap data in chunks
    const size_t CHUNK_SIZE = 512;  // Smaller chunks for ESP32
    size_t totalBytes = widthBytes * height;
    size_t sent = 0;
    
    while (sent < totalBytes) {
      size_t chunkSize = min(CHUNK_SIZE, totalBytes - sent);
      size_t written = writeBytes(bitmapData + sent, chunkSize, false);
      
      if (written != chunkSize) {
        Serial.printf("Warning: Sent %d of %d bytes\n", written, chunkSize);
      }
      
      sent += written;
      serial.flush();
      
      // Progress indicator
      if (sent % 4096 == 0) {
        Serial.printf("  Progress: %d%%\n", (sent * 100) / totalBytes);
      }
      
      delay(10);  // Small delay between chunks
    }
    
    delay(50);
    return true;
  }
  
  // Feed paper (advance by lines)
  void feed(uint8_t lines = 1) {
    uint8_t cmd[] = {ESC, 'd', lines};
    sendCommand(cmd, 3, lines * 50);
  }
  
  // Cut paper (if supported)
  void cut() {
    uint8_t cmd[] = {GS, 'V', 0x00};
    sendCommand(cmd, 3, 500);
  }
};

#endif // THERMAL_PRINTER_H
