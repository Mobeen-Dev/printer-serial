# ESP32-S3 Thermal Printer - Build-up Curve Generator

ESP32-S3 firmware for controlling Epson TM-T88III thermal printers (ESC/POS compatible) to generate and print build-up curve graphs with embedded labels and grid.

## Features

- ✅ ESC/POS protocol support for thermal printers
- ✅ Bitmap graphics generation (512×1280 pixels)
- ✅ Build-up curve patterns (Quadratic & Linear)
- ✅ Real-time LED status indication
- ✅ Serial communication via UART
- ✅ Optimized memory management for ESP32-S3
- ✅ Graph with embedded labels and grid

## Hardware Requirements

### Components
- **ESP32-S3 DevKitC-1** (or compatible)
- **Epson TM-T88III** thermal printer (or ESC/POS compatible)
- **RS232/TTL Converter** (if printer uses RS232)

### Pin Connections

| ESP32-S3 Pin | Function | Connection |
|--------------|----------|------------|
| GPIO 48 | WS2812 LED | Built-in RGB LED |
| GPIO 17 | UART1 TX | Printer RX |
| GPIO 18 | UART1 RX | Printer TX |
| GND | Ground | Printer GND |

**Note:** Most thermal printers use RS232. You'll need a TTL-to-RS232 converter (e.g., MAX3232 module).

### Wiring Diagram

```
ESP32-S3          TTL-RS232          Thermal Printer
  TX (17) ────────> TTL_TX ────────> RS232 RX
  RX (18) <──────── TTL_RX <──────── RS232 TX
  GND ──────────────────────────────> GND
  
  LED (48) ─> WS2812 RGB LED (built-in)
```

## Software Requirements

### Arduino IDE Setup
1. Install **ESP32 Board Support** in Arduino IDE
   - Add URL in Preferences: `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   - Install "esp32" by Espressif Systems

2. Install **FastLED Library**
   - Go to: Sketch → Include Library → Manage Libraries
   - Search "FastLED" and install

### Board Configuration
```
Board: "ESP32S3 Dev Module"
USB CDC On Boot: "Enabled"
CPU Frequency: "240MHz"
Flash Size: "8MB (64Mb)"
Partition Scheme: "Default 4MB with spiffs"
PSRAM: "OPI PSRAM"
Upload Speed: "921600"
```

## Installation

1. **Download the project:**
   ```
   esp32_thermal_printer/
   ├── esp32_thermal_printer.ino
   ├── ThermalPrinter.h
   ├── BitmapCanvas.h
   ├── GraphGenerator.h
   └── Font5x7.h
   ```

2. **Open in Arduino IDE:**
   - Open `esp32_thermal_printer.ino`

3. **Configure serial port:**
   - In code, verify printer connection (default: COM7 on Windows)
   - Change if needed in main sketch

4. **Upload to ESP32-S3:**
   - Connect ESP32-S3 via USB
   - Select correct COM port
   - Click Upload

## Usage

### Automatic Printing
The firmware automatically prints a build-up curve graph on startup.

### Manual Trigger
1. Open Serial Monitor (115200 baud)
2. Send `p` or `P` to trigger a new print

### LED Status Indicators

| Color | Status | Meaning |
|-------|--------|---------|
| **Light Blue** | Processing | Generating graph/printing |
| **Green** | Success | Print completed successfully |
| **Red** | Failure | Error occurred |
| **Black (Off)** | Idle | Ready for next command |

## Graph Output

### Graph Specifications
- **Canvas Size:** 512×1280 pixels
- **X-Axis (Time):** 0 to 30 seconds (step: 2s)
- **Y-Axis (Pressure):** 0 to 200K (step: 25K)
- **Grid:** Dashed lines with 60px/80px spacing

### Build-Up Curve Patterns

#### Pattern 1: Quadratic Rise (Default)
- Starts at 0 pressure
- Rises smoothly to 200K over 26 seconds
- Quadratic acceleration (slow start, fast finish)
- Sudden drop to 0 after peak
- Small random noise (±3)

#### Pattern 2: Linear Rise
- Starts at 0 pressure
- Rises linearly to 200K over 26 seconds
- Steady rate of increase
- Sudden drop to 0 after peak
- Larger random noise (±8)

**To switch patterns:** Edit `PATTERN` variable in `esp32_thermal_printer.ino`:
```cpp
const uint8_t PATTERN = 1;  // 1 = Quadratic, 2 = Linear
```

### Output Structure
```
┌─────────────────────────────────────┐
│    Build-up Curve Graph             │  ← Title
├─────────────────────────────────────┤
│     25K 50K 75K ........... 200K    │  ← Y-axis labels (rotated 90°)
│ ═══╬═══╬═══╬═══╬═══╬═══╬═══╬═══     │  ← Grid
│ 0  ║   ║ /─────────────────\        │
│ 2  ║   ║/                   \       │
│ 4  ║  /                      \      │  ← Curve
│ ...║ /                        \     │
│ 26 ║/                          \    │
│ 28 ║                            \   │
│ 30 ║                             \  │
│    ═══╬═══╬═══╬═══╬═══╬═══╬═══╬═══  │
│         T I M E                     │  ← X-axis label
├─────────────────────────────────────┤
│         P R E S S U R E             │  ← Bottom title
└─────────────────────────────────────┘
```

## Memory Optimization

The firmware is optimized for ESP32-S3's memory constraints:

- **Bitmap Buffer:** ~78KB (512×1280 pixels)
- **Curve Data:** ~19KB (4800 floats)
- **Font Data:** Stored in PROGMEM
- **Chunked Transmission:** 512-byte chunks to printer

**Total RAM Usage:** ~100KB peak

## Troubleshooting

### Printer Not Responding
1. **Check connections:**
   - Verify TX/RX are not swapped
   - Confirm ground connection
   - Test with multimeter if unsure

2. **Check baud rate:**
   - Default: 19200
   - Common alternatives: 9600, 38400, 115200
   - Consult printer manual

3. **Test with ESC/POS commands:**
   ```cpp
   PrinterSerial.write(0x1B);  // ESC
   PrinterSerial.write('@');    // Initialize
   ```

### LED Not Working
- Verify GPIO 48 is correct for your board
- Some boards use GPIO 38 or GPIO 21
- Check FastLED library is installed

### Memory Errors
If you see "Canvas allocation failed":
- Reduce `GRAPH_HEIGHT` in main sketch
- Reduce `GRAPH_WIDTH` (must be multiple of 8)
- Enable PSRAM in board settings

### Print Quality Issues
```cpp
// Adjust density (0-15, higher = darker)
printer->setDensity(10, 2);

// Adjust line spacing
printer->setLineHeight(24);
```

## Serial Monitor Output

```
========================================
ESP32-S3 Thermal Printer
Build-up Curve Generator
========================================
✓ LED initialized
✓ Serial port opened

Configuration:
  Canvas: 512x1280 pixels
  Graph area: 480x1130 pixels
  X-axis: 0 to 30s (step 2s)
  Y-axis: 0 to 200K (step 25K)
  Pattern: Quadratic rise (0→200K in ≤26s → Drop)

========================================

[1/5] Initializing printer...
  ✓ Printer ready

[2/5] Configuring printer...
  ✓ Configuration applied

[3/5] Generating graph...
  Allocating 81920 bytes for canvas...
  ✓ Canvas allocated
  ✓ Canvas created

[4/5] Drawing graph components...
  → Drawing Y-axis labels...
  → Drawing grid...
  → Drawing X-axis labels...
  → Generating build-up curve data...
  ✓ Generated 4800 data points (Pattern 1)
  → Drawing curve...
  ✓ Curve drawn

[5/5] Printing to device...
  → Sending bitmap (512x1280)...
  Progress: 25%
  Progress: 50%
  Progress: 75%
  ✓ Bitmap sent

========================================
✓✓✓ PRINTING COMPLETED! ✓✓✓
========================================
```

## Advanced Customization

### Change Graph Dimensions
```cpp
#define GRAPH_WIDTH  512    // Must be multiple of 8
#define GRAPH_HEIGHT 1200   // Adjust as needed
```

### Modify Grid Spacing
```cpp
#define GRID_X_SPACING 80   // Pixels per time division
#define GRID_Y_SPACING 60   // Pixels per pressure division
```

### Change Axis Ranges
```cpp
#define X_MAX 30    // Maximum time (seconds)
#define X_STEP 2    // Time step (seconds)
#define Y_MAX 200   // Maximum pressure (K)
#define Y_STEP 25   // Pressure step (K)
```

### Adjust Curve Thickness
In `esp32_thermal_printer.ino`, modify the `drawCurve()` call:
```cpp
generator.drawCurve(curveData, 4800, 3);  // Thickness: 1-6
```

## Code Structure

```
esp32_thermal_printer.ino  ← Main sketch
    ├── LED status indication
    ├── Print job orchestration
    └── Serial command handling

ThermalPrinter.h          ← ESC/POS protocol
    ├── Printer initialization
    ├── Text formatting
    └── Bitmap printing

BitmapCanvas.h            ← Graphics engine
    ├── Pixel manipulation
    ├── Line drawing
    └── Text rendering

GraphGenerator.h          ← Graph creation
    ├── Grid generation
    ├── Label placement
    ├── Curve data generation
    └── Curve plotting

Font5x7.h                 ← Character data
    └── 5×7 pixel font (PROGMEM)
```

## ESC/POS Commands Reference

| Command | Code | Description |
|---------|------|-------------|
| Initialize | `ESC @` | Reset printer to defaults |
| Density | `0x12 0x23 [val]` | Set print darkness |
| Line Height | `ESC 3 [val]` | Set line spacing |
| Align | `ESC a [0-2]` | Left/Center/Right |
| Font Size | `GS ! [size]` | Width/height multiplier |
| Print Bitmap | `GS v 0 ...` | Raster bitmap mode |
| Feed | `ESC d [lines]` | Advance paper |

## Contributing

Contributions welcome! Areas for improvement:
- Additional curve patterns
- Multi-page graphs
- Real-time data plotting
- WiFi/Bluetooth control
- Configuration via web interface

## License

MIT License - Free to use and modify

## Credits

Based on Python thermal printer script, converted for ESP32-S3 embedded systems.

## Support

For issues or questions:
1. Check troubleshooting section
2. Review serial monitor output
3. Test with minimal example
4. Open GitHub issue with details

---

**Happy Printing! 🖨️**
