# Copilot Instructions — Printer Serial (ESP32 Thermal Printer)

> **Read this file in full before writing a single line of code.**
> It governs both human developers and AI agents working on this repo.
> When in doubt about anything, re-read the relevant section rather than making an assumption.

---

## Repo Layout

This project has two independent but conceptually mirrored sides that share the same printing goal — generating a 1-bit bitmap graph and sending it to an **Epson TM-T88III** thermal printer via ESC/POS.

**Python (host-side):** Scripts in the repo root, `tests\`, and `visualize\`. These run on a PC, generate bitmaps in software, and push them to the printer over a USB-serial COM port.

**Embedded (device-side):** `embedded\esp32_thermal_printer\` — an Arduino sketch for the **ESP32-S3** that renders the same style of graph into a 1-bit canvas entirely in firmware, then prints over hardware UART to the printer. The five core firmware files are:

```
esp32_thermal_printer.ino   ← Orchestrator; runs printGraph() and LED signalling
GraphGenerator.h            ← Grid, labels, and curve drawing into the canvas
BitmapCanvas.h              ← Raw 1-bit pixel buffer + Bresenham drawing primitives
ThermalPrinter.h            ← ESC/POS UART driver (chunked bitmap send)
Font5x7.h                   ← 5×7 PROGMEM bitmap font (digits + subset of letters)
```

**The full embedded data pipeline is:**
```
DataSource → GraphGenerator → BitmapCanvas → ThermalPrinter → Physical Paper
```
Understanding this pipeline end-to-end is mandatory before editing any firmware file. A mistake in byte layout or pixel coordinates will produce silent garbage on paper — there is no runtime exception.

---

## Quick Commands

### Python Setup
```powershell
pip install -r requirements.txt
```

### Discover Serial Ports
```powershell
python inspectSerialPorts.py
```

### Run the Main Graph Script
```powershell
python plotGraphFromTerminal.py
```

### Run Test Scripts (not a pytest suite — these are standalone runnable scripts)
```powershell
python tests\grid_test.py
python tests\grid_test8.py
```

### Compile Embedded Firmware (ESP32-S3)
```powershell
arduino-cli compile --fqbn esp32:esp32:esp32s3 embedded\esp32_thermal_printer
```

---

## Serial & Printer Conventions

COM ports are often hardcoded in scripts (commonly `COM7`). Change the `port=` argument if your setup differs. Baud rates vary by script — `19200` is common in `tests\grid_test7.py`, `9600` elsewhere. Printing uses ESC/POS raster/bitmap commands. Large bitmaps are always **chunked** during transmission to avoid UART buffer overflow.

---

## Graphics & Bitmap Conventions (Shared Across Python + Embedded)

Bitmaps are strictly 1-bit monochrome. Printer width must always be **byte-aligned**: `width % 8 == 0`, because raster rows are `width / 8` bytes wide. Violating this produces corrupted output. The canvas is **512 px wide × 1280 px tall** (GRAPH_HEIGHT 1200 + TOP_MARGIN 70 + BOTTOM_MARGIN 10). Graph rendering always follows this sequence: draw grid lines → draw axis labels → draw curve → send bitmap. Label rendering uses 5×7 font glyphs with 90° rotation for axis labels.

---

## Embedded Firmware Conventions

### Language & Runtime Rules
The firmware must remain Arduino/ESP32-core friendly at all times. This means: no exceptions, no RTTI, no `std::` containers. Use raw pointers and `malloc` / `free` for heap allocation — match what already exists. Use `int16_t`, `uint16_t`, `uint8_t` etc. (fixed-width types) rather than plain `int` or `long`, because sizes are architecture-dependent. Use `Serial.printf("  ✓ ...\n")` style for all status and progress logging — this is the established convention throughout the codebase.

### PROGMEM Rules
PROGMEM is used for all read-only data (fonts, hardcoded datasets). When reading from a PROGMEM array, always use the appropriate helper macro — `pgm_read_word()` for `int16_t` / `uint16_t` values, `pgm_read_byte()` for `uint8_t`. Never dereference a PROGMEM pointer directly. On some architectures this causes silent data corruption. PROGMEM arrays must be declared at **file scope** or as **static class members** — not as local function variables.

### Data Type Selection Rationale
For curve data (values range 0–200): use `int16_t`. Here is why `int16_t` beats the alternatives — `uint8_t` (0–255) is unsigned and breaks during signed arithmetic inside the moving average; `float` is 4 bytes and wastes flash for a 2400-element array; `int` is also 4 bytes on ESP32; `int16_t` is signed, 2 bytes, handles all intermediate math safely. This is the correct embedded choice.

---

## Data Source HAL (Hardware Abstraction Layer)

This is the most important architectural concept in the embedded side. The curve data source is **fully decoupled** from the renderer and printer. Neither `GraphGenerator` nor `ThermalPrinter` knows or cares where data comes from. The abstraction is implemented as a C++ abstract base class hierarchy — the standard embedded HAL pattern.

### Abstract Base Class — `DataSource`
Declares four pure virtual methods and a virtual destructor. Nothing else — no data members, no default implementations, no helper utilities. The virtual destructor is mandatory because the `.ino` orchestrator deletes through a base class pointer.

```cpp
class DataSource {
public:
  virtual bool initialize() = 0;
  virtual bool fetchData() = 0;        // Populate internal buffer
  virtual const int16_t* getData() const = 0;
  virtual uint16_t getDataLength() const = 0;
  virtual ~DataSource() {}
};
```

### Active Concrete Source — `HardcodedDataSource`
PROGMEM-backed. Stores 2400 `int16_t` values in flash. `initialize()` and `fetchData()` both simply return `true` — no hardware interaction needed. `getData()` returns the PROGMEM pointer. No heap allocation anywhere in this class. The array currently contains representative sample values; look for the marker comment `// 2400-values` to locate where the full dataset should be inserted.

### Future Concrete Source — `UARTDataSource`
Fully stubbed. All methods return safe disabled values (`false`, `nullptr`, `0`). Guarded by `#define UART_DATASOURCE_ENABLED 0` at the top of the file — this define makes it unambiguously clear the class is not operational. FUTURE PROTOCOL: UART, 2400 × `int16_t` values, range 0–200, blocking read with timeout in `fetchData()`. When implementing, do not put any blocking or timing logic in `DataSource` files — that belongs in the `.ino` orchestrator.

### Swapping the Data Source
To switch from hardcoded to UART data, change exactly **one line** in `esp32_thermal_printer.ino`:
```cpp
// Change this:
DataSource* dataSource = new HardcodedDataSource();
// To this:
DataSource* dataSource = new UARTDataSource(PrinterSerial, 115200, 2400);
```
No other file should require any change. If a proposed implementation requires changes beyond this one line, the abstraction is broken — stop and fix the design first.

---

## Editing Guidelines

### Files That Are Sealed (Do Not Touch)
`BitmapCanvas.h`, `ThermalPrinter.h`, and `Font5x7.h` are **read-only** unless a task explicitly and specifically requires modifying them. Do not touch them for cleanup, reformatting, or "while I'm in here" improvements. Treat them as third-party library headers.

### Preserving Visual Output
When refactoring any data or curve logic, the printed graph must remain visually identical. Grid lines, label positions, axis layout, line thickness — none of these may change. The only thing that should change is where the curve data comes from, not how it is drawn.

### Scope Discipline
Do not refactor code outside the task's stated scope, even if you notice an improvement opportunity. Untargeted refactoring in embedded systems introduces silent risk. If `drawGrid()` looks inefficient, note it in a comment and move on. Fix it in a dedicated task.

### Comment Standards
Use `//` for inline and single-line comments. Use `/* */` only for multi-line block comments at the top of files or functions. Never leave commented-out code without explaining why it was commented out. Every `TODO:` must state what needs to be done and what information is still missing to do it. Every new file must begin with a header block matching the style of existing files — filename, one-line description, brief notes on contents.

---

## `drawCurve()` — Modification Rules

This function is the bridge between data and pixels. It does three things in sequence: max-pool downsampling (reduces 2400 input points to ~1130 canvas rows), moving average smoothing (11-point window, `applyMovingAverage()`), and Bresenham line-segment drawing. All three behaviors must be preserved across any refactor.

When the input type changes from `float*` to `int16_t*`, the internal arithmetic must be handled carefully. The scale factor must remain `float`: `float scale = (float)graphWidth / yMax`. All multiplications involving a data value must cast explicitly: `(float)val * scale`. The `constrain()` call must use typed casts to avoid ambiguity: `constrain(val, (int16_t)0, (int16_t)yMax)`. The `applyMovingAverage()` temp buffer and accumulator must stay as `float` internally for precision, then cast back to `int16_t` when storing results — accumulating in `int16_t` risks overflow on window sizes above 5.

The max-pooling loop has an off-by-one sensitivity: `uint16_t end = (uint16_t)((i + 1) * ratio)` can equal `dataLen` on the last iteration. The inner guard `j < dataLen` already handles this — do not remove it. The `malloc` return value inside `applyMovingAverage()` must always be checked before use — preserve this existing check.

---

## Risk Areas — Be Especially Careful

**`graphWidth` math:** The value is computed in `GraphGenerator`'s constructor as `gridYSpacing * (yMax / yStep)`. This is integer division. Verify it still equals `480` after any change by tracing through: 60 (gridYSpacing) × (200 / 25) = 60 × 8 = 480. If this ever changes, all pixel X coordinates shift silently.

**PROGMEM pointer lifetime:** The pointer returned by `HardcodedDataSource::getData()` points to flash. Do not call `free()` on it. Do not store it past the lifetime of the `HardcodedDataSource` object.

**`nullptr` guard:** `UARTDataSource::getData()` returns `nullptr` when disabled. The `.ino` orchestrator must check `curveData != nullptr` before passing to `drawCurve()`. If this check is missing, the system will hard-fault silently on hardware.

**`delete` ordering:** In `printGraph()`, delete in this order: `delete dataSource` first (calls virtual destructor, frees UART buffer if allocated), then `delete canvas`. Reversing this order is safe here but incorrect as a general habit.

**Canvas byte alignment:** The canvas width of 512 px = 64 bytes per row. Never change `CANVAS_WIDTH` to a non-multiple of 8. The printer will silently shift every row if this invariant is broken.

---

## Definition of Done

An implementation is complete only when all of the following are true. Do not declare done until every point is verified.

The project compiles on ESP32-S3 Arduino core with **zero errors and zero warnings**. In embedded systems, every warning is a potential runtime bug — treat warnings as errors.

Swapping `new HardcodedDataSource()` to `new UARTDataSource(...)` in the one designated line requires zero other changes anywhere. This is the proof the abstraction is correct.

The printed graph is visually identical to the output of the original formula-based code — same grid, same margins, same label positions, same curve shape.

No `float*` exists in the data path between `DataSource` and `drawCurve()`. Type conversion happened at data-source time, not inside the renderer.

`free()` is not called on the pointer returned by `HardcodedDataSource::getData()`.

The `// 2400-values` marker comment is present at the correct location in `HardcodedDataSource.h`.

`BitmapCanvas.h`, `ThermalPrinter.h`, and `Font5x7.h` are byte-for-byte identical to their state before the task began.

---

## Pre-Submission Checklist

Work through this list item by item. Do not submit output until every box can be checked.

- [ ] `DataSource.h` contains no data members and no method implementations
- [ ] `HardcodedDataSource.h` includes no UART or hardware-specific headers
- [ ] `UARTDataSource.h` has `#define UART_DATASOURCE_ENABLED 0` at the top
- [ ] `UARTDataSource.h` compiles cleanly with the define set to `0`
- [ ] `UARTDataSource.h` contains the `FUTURE IMPLEMENTATION NOTES` comment block
- [ ] `GraphGenerator.h` has no `generateBuildUpCurve()`, no `randSeed`, no `random_float()`
- [ ] `drawCurve()` signature is `void drawCurve(const int16_t* rawData, uint16_t dataLen, uint8_t thickness = 1)`
- [ ] `applyMovingAverage()` uses `float` internally and casts to `int16_t` on output
- [ ] `esp32_thermal_printer.ino` has no `free(curveData)` call
- [ ] `esp32_thermal_printer.ino` has `delete dataSource` before `delete canvas`
- [ ] The swap comment `// DATA SOURCE — swap HardcodedDataSource for UARTDataSource when IC is ready` is present above the instantiation line
- [ ] The `// 2400-values` marker is present in `HardcodedDataSource.h`
- [ ] `nullptr` check on `getData()` return value is present in `.ino` before `drawCurve()` call
- [ ] No STL containers (`std::vector`, `std::array`, etc.) used anywhere in new or modified files
- [ ] All new files use `#ifndef FILE_NAME_H` header guard convention
- [ ] All new files have the standard header comment block (filename, description, notes)
- [ ] `BitmapCanvas.h`, `ThermalPrinter.h`, `Font5x7.h` are unmodified