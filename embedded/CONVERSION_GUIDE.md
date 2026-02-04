# Python to ESP32-S3 Conversion Guide

This document shows how the original Python thermal printer code was converted to ESP32-S3 C++.

---

## Architecture Comparison

| Aspect | Python (Original) | ESP32-S3 (Converted) |
|--------|-------------------|----------------------|
| Language | Python 3 | C++ (Arduino) |
| Platform | PC/Raspberry Pi | ESP32-S3 Microcontroller |
| Memory | Unlimited | 512KB RAM + 8MB PSRAM |
| Processing | Single-threaded | Multi-tasking (FreeRTOS) |
| Libraries | pyserial, time, random | FastLED, HardwareSerial |

---

## Code Structure Mapping

### Python Classes → ESP32 Headers

| Python Class | ESP32 Header | Purpose |
|--------------|--------------|---------|
| `EpsonThermalPrinter` | `ThermalPrinter.h` | Printer control |
| `BitmapCanvas` | `BitmapCanvas.h` | Graphics rendering |
| `generate_sample_data()` | `GraphGenerator.h` | Curve generation |
| `create_complete_graph()` | `GraphGenerator.h` | Graph assembly |

---

## Feature-by-Feature Comparison

### 1. Serial Communication

**Python:**
```python
import serial

self.ser = serial.Serial(
    port="COM7",
    baudrate=19200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=3,
    xonxoff=True
)
```

**ESP32:**
```cpp
#include <HardwareSerial.h>

HardwareSerial PrinterSerial(1);

void setup() {
  PrinterSerial.begin(19200, SERIAL_8N1, 18, 17);
  // RX=18, TX=17
}
```

---

### 2. ESC/POS Commands

**Python:**
```python
ESC = b"\x1b"
GS = b"\x1d"

def begin(self):
    self.ser.write(ESC + b"@")
    time.sleep(0.5)
```

**ESP32:**
```cpp
#define ESC 0x1B
#define GS  0x1D

bool begin() {
  uint8_t init[] = {ESC, '@'};
  return sendCommand(init, 2, 500);
}
```

---

### 3. Bitmap Canvas

**Python:**
```python
class BitmapCanvas:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.bytes_per_line = width // 8
        self.data = bytearray(self.bytes_per_line * height)
```

**ESP32:**
```cpp
class BitmapCanvas {
private:
  uint16_t width, height;
  uint16_t bytesPerLine;
  uint8_t* data;
  
public:
  BitmapCanvas(uint16_t w, uint16_t h) {
    width = w;
    height = h;
    bytesPerLine = w / 8;
    data = (uint8_t*)malloc(bytesPerLine * height);
  }
};
```

---

### 4. Pixel Drawing

**Python:**
```python
def set_pixel(self, x, y):
    if x < 0 or x >= self.width or y < 0 or y >= self.height:
        return
    
    byte_index = (x // 8) + y * self.bytes_per_line
    bit_position = x & 7
    self.data[byte_index] |= 0x80 >> bit_position
```

**ESP32:**
```cpp
void setPixel(int16_t x, int16_t y) {
  if (x < 0 || x >= width || y < 0 || y >= height) {
    return;
  }
  
  uint32_t byteIndex = (x / 8) + y * bytesPerLine;
  uint8_t bitPosition = x & 7;
  data[byteIndex] |= (0x80 >> bitPosition);
}
```

---

### 5. Random Number Generation

**Python:**
```python
import random

noise = random.uniform(-3, 3)
```

**ESP32:**
```cpp
// Custom LCG (Linear Congruential Generator)
uint32_t randSeed;

float random_float(float min_val, float max_val) {
  randSeed = (1103515245 * randSeed + 12345) & 0x7FFFFFFF;
  float r = (float)randSeed / 0x7FFFFFFF;
  return min_val + r * (max_val - min_val);
}

// Usage:
randSeed = micros();  // Initialize
float noise = random_float(-3.0, 3.0);
```

---

### 6. Build-Up Curve Generation

**Python:**
```python
def generate_sample_data(num_points=4800, pattern=1):
    data = []
    rise_points = int(num_points * (26.0 / 30.0))
    
    if pattern == 1:
        for i in range(rise_points):
            progress = i / rise_points
            base_value = 200 * (progress ** 2)
            noise = random.uniform(-3, 3)
            data.append(max(0, min(200, base_value + noise)))
    
    # Drop to 0
    for _ in range(num_points - rise_points):
        data.append(0)
    
    return data
```

**ESP32:**
```cpp
float* generateBuildUpCurve(uint16_t numPoints, uint8_t pattern) {
  float* data = (float*)malloc(numPoints * sizeof(float));
  uint16_t risePoints = (numPoints * 26) / 30;
  
  if (pattern == 1) {
    for (uint16_t i = 0; i < risePoints; i++) {
      float progress = (float)i / risePoints;
      float baseValue = 200.0 * (progress * progress);
      float noise = random_float(-3.0, 3.0);
      data[i] = constrain(baseValue + noise, 0, 200);
    }
  }
  
  // Drop to 0
  for (uint16_t i = risePoints; i < numPoints; i++) {
    data[i] = 0;
  }
  
  return data;
}
```

---

### 7. Bitmap Printing

**Python:**
```python
def print_bitmap(self, width, height, bitmap_data):
    width_bytes = width // 8
    
    cmd = GS + b"v0"
    cmd += bytes([0])
    cmd += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])
    cmd += bytes([height & 0xFF, (height >> 8) & 0xFF])
    
    self.ser.write(cmd)
    
    chunk_size = 4096
    for i in range(0, len(bitmap_data), chunk_size):
        chunk = bitmap_data[i:i + chunk_size]
        self.ser.write(chunk)
```

**ESP32:**
```cpp
bool printBitmap(uint16_t width, uint16_t height, 
                 const uint8_t* bitmapData) {
  uint16_t widthBytes = width / 8;
  
  uint8_t cmd[] = {
    GS, 'v', '0',
    0x00,
    (uint8_t)(widthBytes & 0xFF),
    (uint8_t)((widthBytes >> 8) & 0xFF),
    (uint8_t)(height & 0xFF),
    (uint8_t)((height >> 8) & 0xFF)
  };
  
  sendCommand(cmd, 8, 20);
  
  // Send in smaller chunks for ESP32
  const size_t CHUNK_SIZE = 512;
  size_t totalBytes = widthBytes * height;
  
  for (size_t sent = 0; sent < totalBytes; sent += CHUNK_SIZE) {
    size_t chunkSize = min(CHUNK_SIZE, totalBytes - sent);
    serial.write(bitmapData + sent, chunkSize);
    serial.flush();
    delay(10);
  }
  
  return true;
}
```

---

## Key Differences

### Memory Management

**Python:**
- Automatic garbage collection
- Dynamic memory allocation is cheap
- No memory constraints

**ESP32:**
- Manual memory management (`malloc`/`free`)
- Limited RAM (512KB + PSRAM)
- Must deallocate resources
- Use `PROGMEM` for constants

### Data Types

| Python | ESP32 | Notes |
|--------|-------|-------|
| `int` | `int16_t`, `uint16_t` | Explicit sizing |
| `float` | `float` | Same precision |
| `bytes` | `uint8_t*` | Raw byte arrays |
| `list` | `float*` (malloc) | Dynamic arrays |
| `str` | `char*` | C-strings |

### Timing

**Python:**
```python
import time
time.sleep(0.5)  # 500ms delay
```

**ESP32:**
```cpp
delay(500);  // 500ms delay (blocking)
vTaskDelay(pdMS_TO_TICKS(500));  // FreeRTOS (non-blocking)
```

---

## Additional Features in ESP32 Version

### 1. LED Status Indication

**Not in Python - New Feature:**
```cpp
#include <FastLED.h>

CRGB leds[NUM_LEDS];

void indicateProcessing() {
  leds[0] = CRGB(0, 191, 255);  // Light Blue
  FastLED.show();
}

void indicateSuccess() {
  leds[0] = CRGB::Green;
  FastLED.show();
}

void indicateFailure() {
  leds[0] = CRGB::Red;
  FastLED.show();
}
```

### 2. FreeRTOS Task Structure

**Not in Python - New Feature:**
```cpp
// Separate tasks for different functions
xTaskCreatePinnedToCore(taskLED, "LED", 2048, NULL, 2, NULL, 1);
xTaskCreatePinnedToCore(taskSerialCmd, "Cmd", 4096, NULL, 1, NULL, 0);
xTaskCreatePinnedToCore(taskPrintJob, "Print", 8192, NULL, 1, NULL, 0);

// Thread-safe status updates
SemaphoreHandle_t statusMutex;
QueueHandle_t printQueue;
```

### 3. Error Handling

**Python:**
```python
try:
    printer = EpsonThermalPrinter(port="COM7")
    # ... code ...
except Exception as e:
    print(f"Error: {e}")
finally:
    printer.close()
```

**ESP32:**
```cpp
if (!printer->begin()) {
  Serial.println("✗ Printer initialization failed!");
  indicateFailure();
  return;
}

// Explicit cleanup
if (data) {
  free(data);
  data = nullptr;
}
```

---

## Performance Considerations

### Python Script
- Runs on PC/Raspberry Pi
- Fast floating-point math
- No memory concerns
- Can use large buffers

### ESP32-S3 Firmware
- Embedded microcontroller
- Limited RAM (optimize allocations)
- Chunked transmission (512 bytes)
- PROGMEM for font data
- Careful with stack usage

---

## Migration Checklist

When converting similar Python thermal printer scripts:

- [ ] Convert `serial.Serial` to `HardwareSerial`
- [ ] Replace `bytearray` with `uint8_t*` + `malloc`
- [ ] Replace `time.sleep()` with `delay()` or `vTaskDelay()`
- [ ] Replace `random.uniform()` with custom RNG
- [ ] Convert classes to C++ classes/headers
- [ ] Add manual memory management (`free()`)
- [ ] Reduce chunk sizes for transmission
- [ ] Add LED status indicators
- [ ] Implement error handling
- [ ] Test memory usage (keep < 80% RAM)
- [ ] Add serial debugging output

---

## Testing Strategy

### Python Version
```bash
python thermal_printer.py
```

### ESP32 Version
1. Upload firmware via Arduino IDE
2. Open Serial Monitor (115200 baud)
3. Watch for status messages
4. Monitor LED colors
5. Send 'p' to trigger print

---

## File Size Comparison

| Component | Python | ESP32 |
|-----------|--------|-------|
| Main script | 15 KB | 5 KB (.ino) |
| Printer class | In main | 4 KB (.h) |
| Canvas class | In main | 3 KB (.h) |
| Graph generator | In main | 5 KB (.h) |
| Font data | In main | 2 KB (.h) |
| **Total** | ~15 KB | ~19 KB |

ESP32 firmware is slightly larger due to:
- Header file structure
- Additional error handling
- LED control code
- FreeRTOS integration

---

## Summary

The ESP32-S3 conversion maintains **100% functional parity** with the Python version while adding:

✅ Real-time LED status indication  
✅ FreeRTOS multi-tasking  
✅ Serial command interface  
✅ Thread-safe operation  
✅ Optimized memory usage  
✅ Hardware integration  

The core algorithms (curve generation, bitmap rendering, ESC/POS commands) are **identical** in both versions.
