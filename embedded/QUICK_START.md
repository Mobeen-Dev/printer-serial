# ESP32-S3 Thermal Printer - Quick Start Guide

## 📦 What You Got

I've converted your Python thermal printer code into a complete ESP32-S3 firmware project with the following enhancements:

### ✅ Core Features
- **ESC/POS Protocol**: Full Epson TM-T88III compatibility
- **Bitmap Graphics**: 512×1280 pixel canvas rendering
- **Build-up Curves**: Two pattern options (Quadratic & Linear)
- **LED Status**: Light Blue → Green/Red indication
- **Serial Communication**: UART1 for printer control

### 📁 Project Files

```
esp32_thermal_printer/
├── esp32_thermal_printer.ino          ← Main sketch (simple)
├── esp32_thermal_printer_advanced.ino ← FreeRTOS version
├── ThermalPrinter.h                   ← Printer control
├── BitmapCanvas.h                     ← Graphics engine
├── GraphGenerator.h                   ← Curve generation
├── Font5x7.h                          ← Character rendering
├── README.md                          ← Full documentation
└── CONVERSION_GUIDE.md                ← Python → ESP32 mapping
```

---

## 🚀 5-Minute Setup

### 1. Hardware Connections

```
ESP32-S3 DevKitC-1:
  GPIO 48 → WS2812 RGB LED (built-in)
  GPIO 17 → Printer RX (via TTL-RS232 converter)
  GPIO 18 → Printer TX (via TTL-RS232 converter)
  GND     → Printer GND
```

### 2. Arduino IDE Configuration

**Board Settings:**
- Board: "ESP32S3 Dev Module"
- USB CDC On Boot: "Enabled"
- Flash Size: "8MB"
- PSRAM: "OPI PSRAM"

**Install Libraries:**
- FastLED (via Library Manager)

### 3. Upload & Run

1. Open `esp32_thermal_printer.ino`
2. Click **Upload**
3. Watch LED turn **Light Blue** (processing)
4. LED turns **Green** on success!

---

## 🎨 LED Status Codes

| Color | Status | What It Means |
|-------|--------|---------------|
| 🔵 **Light Blue** | Processing | Generating graph/printing |
| 🟢 **Green** | Success | Print completed! |
| 🔴 **Red** | Failure | Something went wrong |
| ⚫ **Off** | Idle | Ready for next job |

---

## 📊 Output Example

Your ESP32 will print a graph like this:

```
╔═══════════════════════════════════════╗
║    Build-up Curve Graph               ║
╠═══════════════════════════════════════╣
║ 25K 50K 75K 100K 125K 150K 175K 200K  ║ ← Pressure labels
║ ═══╬═══╬═══╬═══╬═══╬═══╬═══╬═══      ║
║ 0  ║   ║ ╱─────────────────╲          ║
║ 2  ║   ║╱                   ╲         ║ ← Time (seconds)
║ 4  ║  ╱                      ╲        ║
║ 6  ║ ╱                        ╲       ║
║... ║╱                          ╲      ║
║ 26 ╱                            ╲     ║
║ 28                               ╲    ║
║ 30                                ╲0  ║
║    T I M E                            ║
╠═══════════════════════════════════════╣
║         P R E S S U R E               ║
╚═══════════════════════════════════════╝
```

---

## 🎮 Two Versions Included

### Basic Version (`esp32_thermal_printer.ino`)
- **Best for:** Simple, one-time printing
- **Runs:** Automatically on startup
- **Trigger:** Send 'p' via Serial Monitor
- **Memory:** ~100KB RAM usage

### Advanced Version (`esp32_thermal_printer_advanced.ino`)
- **Best for:** Multi-tasking, command control
- **Features:** FreeRTOS tasks, print queue
- **Commands:**
  - `P1` = Print Pattern 1 (Quadratic)
  - `P2` = Print Pattern 2 (Linear)
  - `S` = Status query
- **Advantages:** Non-blocking, thread-safe

---

## 📝 Serial Monitor Output

```
========================================
ESP32-S3 Thermal Printer
Build-up Curve Generator
========================================
✓ LED initialized
✓ Serial port opened

[1/5] Initializing printer...
  ✓ Printer ready

[2/5] Configuring printer...
  ✓ Configuration applied

[3/5] Generating graph...
  Allocating 81920 bytes for canvas...
  ✓ Canvas allocated

[4/5] Drawing graph components...
  → Drawing Y-axis labels...
  → Drawing grid...
  → Generating curve data...
  ✓ Generated 4800 data points

[5/5] Printing to device...
  Progress: 25%
  Progress: 50%
  Progress: 75%
  ✓ Bitmap sent

========================================
✓✓✓ PRINTING COMPLETED! ✓✓✓
========================================
```

---

## 🔧 Quick Customization

### Change Curve Pattern
In main sketch:
```cpp
float* curveData = generator.generateBuildUpCurve(4800, 1);
                                                        ↑
                                                   1 or 2
```

### Adjust Print Density
```cpp
printer->setDensity(10, 2);  // 0-15, higher = darker
                      ↑
```

### Modify Graph Size
```cpp
#define GRAPH_WIDTH  512   // Must be multiple of 8
#define GRAPH_HEIGHT 1200  // Adjust as needed
```

---

## 🐛 Common Issues

### LED Not Working?
- Check GPIO 48 (some boards use GPIO 38)
- Verify FastLED library installed

### Printer Not Responding?
1. Verify TX/RX not swapped
2. Check baud rate (default: 19200)
3. Test with: `PrinterSerial.write(0x1B); PrinterSerial.write('@');`

### Memory Error?
- Enable PSRAM in board settings
- Reduce `GRAPH_HEIGHT` value

---

## 📚 Full Documentation

- **README.md** - Complete hardware setup, configuration, troubleshooting
- **CONVERSION_GUIDE.md** - Detailed Python → ESP32 code comparison
- **Code comments** - Every function documented inline

---

## 🎯 Key Improvements Over Python

✅ **Real-time Status LEDs** - Visual feedback at a glance  
✅ **FreeRTOS Tasks** - True multi-tasking capability  
✅ **Embedded System** - Standalone operation, no PC needed  
✅ **Serial Commands** - Remote triggering via UART  
✅ **Memory Optimized** - Works within ESP32 constraints  
✅ **Error Handling** - Robust failure recovery  

---

## 💡 Next Steps

1. **Test Basic Version First**
   - Upload `esp32_thermal_printer.ino`
   - Verify LED and printer work

2. **Try Advanced Version**
   - Upload `esp32_thermal_printer_advanced.ino`
   - Test serial commands (P1, P2, S)

3. **Customize for Your Needs**
   - Modify graph parameters
   - Change curve patterns
   - Adjust print quality

---

## 📞 Need Help?

Check the README.md for:
- Detailed hardware setup
- Pin connection diagrams
- Troubleshooting guide
- ESC/POS command reference
- Memory optimization tips

**Happy Printing! 🖨️**
