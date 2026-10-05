# ESP32-S3 Thermal Printer Firmware

Firmware for an **ESP32-S3 DevKitC-1** that renders a load graph as a 1-bit bitmap and prints it to an **Epson TM-T88III** thermal printer using ESC/POS commands.

The active sketch is in `esp32_thermal_printer\`.

## Features

- Renders the graph completely on the ESP32-S3.
- Uses a 512-pixel-wide, byte-aligned monochrome canvas.
- Draws dashed grid lines, rotated axis labels, and a smoothed curve.
- Uses a 750-sample `int16_t` data source stored in PROGMEM.
- Sends the bitmap to the printer in 512-byte chunks.
- Uses a `DataSource` hardware-abstraction interface so a future UART/IC source can replace the hardcoded source.
- Signals print status with the onboard WS2812 LED.
- Automatically prints once during startup.
- Accepts `p` or `P` from the USB serial monitor to print again.

## Project structure

```text
embedded\
├── Readme.md                         This current firmware guide
├── QUICK_START.md                    Older quick-start reference
├── Details.md                        Older architecture notes
├── CONVERSION_GUIDE.md               Python-to-ESP32 comparison
└── esp32_thermal_printer\
    ├── esp32_thermal_printer.ino     Setup, print workflow, and orchestration
    ├── DataSource.h                   Abstract data-source interface
    ├── HardcodedDataSource.h          Active 750-sample PROGMEM source
    ├── UARTDataSource.h               Disabled future UART source stub
    ├── GraphGenerator.h               Grid, labels, smoothing, and curve rendering
    ├── BitmapCanvas.h                 1-bit canvas and drawing primitives
    ├── ThermalPrinter.h               ESC/POS UART driver
    └── Font5x7.h                      PROGMEM 5×7 font
```

## Hardware

### Required hardware

- ESP32-S3 DevKitC-1 or compatible ESP32-S3 board
- Epson TM-T88III or another compatible ESC/POS printer
- TTL-to-RS232 converter when the printer exposes RS232 levels
- USB cable for programming and serial-monitor access

### Wiring

| ESP32-S3 | Function | Connect to |
|---|---|---|
| GPIO 17 | UART1 TX | Printer RX through the level converter |
| GPIO 18 | UART1 RX | Printer TX through the level converter |
| GND | Signal ground | Printer GND |
| GPIO 48 | WS2812 data | Built-in RGB LED |

Do not connect ESP32-S3 3.3 V UART signals directly to a true RS232 port. Use an appropriate level converter and verify the printer's electrical interface first.

## Software setup

### Arduino IDE

1. Install ESP32 board support from Espressif.
2. Install the **FastLED** library.
3. Select an ESP32-S3 board, such as **ESP32S3 Dev Module**.
4. Enable PSRAM when available.
5. Open `embedded\esp32_thermal_printer\esp32_thermal_printer.ino`.

### Arduino CLI

From the repository root:

```powershell
arduino-cli compile --fqbn esp32:esp32:esp32s3 embedded\esp32_thermal_printer
arduino-cli upload -p COM<n> --fqbn esp32:esp32:esp32s3 embedded\esp32_thermal_printer
```

Replace `COM<n>` with the port assigned to the ESP32-S3.

## Current graph configuration

The values are defined at the top of `esp32_thermal_printer.ino`:

| Setting | Current value | Meaning |
|---|---:|---|
| `GRAPH_WIDTH` | 512 px | Canvas width; must remain divisible by 8 |
| `GRAPH_HEIGHT` | 750 px | Plotted graph height |
| `TOP_MARGIN` | 70 px | Space before the graph area |
| `BOTTOM_MARGIN` | 40 px | Space after the graph area |
| Total canvas | 512 × 860 px | `750 + 70 + 40` |
| `X_MAX` | 30 s | Time-axis maximum |
| `X_STEP` | 3 s | Time-axis grid interval |
| `GRID_X_SPACING` | 75 px | 10 time divisions across 750 px |
| `Y_MAX` | 200 | Load/pressure scale maximum |
| `Y_STEP` | 25 | Eight vertical divisions |
| `GRID_Y_SPACING` | 60 px | 480 px graph width |
| Printer baud | 19200 | UART1 printer connection |

The canvas uses 64 bytes per row, so the current bitmap allocation is:

```text
64 × 860 = 55,040 bytes
```

The graph area itself is 480 × 750 pixels. The remaining width is used for the left margin and labels.

## Runtime flow

`setup()` performs the following:

1. Sets the printer TX/RX pins and starts the USB debug serial port at 115200 baud.
2. Initializes the WS2812 LED.
3. Starts `PrinterSerial` as UART1 at 19200 baud.
4. Creates the printer object.
5. Runs `printGraph()`.

`printGraph()` then:

1. Resets and initializes the printer.
2. Allocates and clears the bitmap canvas.
3. Creates `GraphGenerator` with the current graph parameters.
4. Draws Y-axis labels, the grid, and X-axis labels.
5. Initializes and fetches data from the configured `DataSource`.
6. Draws the curve.
7. Prints the title, timestamp, sample-number line, and `Load (kN)` text.
8. Sends the bitmap using the ESC/POS `GS v 0` raster command.
9. Releases the canvas and marks the print successful.

The main loop waits for `p` or `P` on the USB serial connection and starts another print job.

## Data-source architecture

### `DataSource`

`DataSource.h` defines the interface used by the orchestrator:

```cpp
class DataSource {
public:
  virtual bool initialize() = 0;
  virtual bool fetchData() = 0;
  virtual const int16_t* getData() const = 0;
  virtual uint16_t getDataLength() const = 0;
  virtual ~DataSource() {}
};
```

The graph renderer does not know whether samples came from flash, UART, or another source.

### `HardcodedDataSource`

This is the active source:

- Stores `750` `int16_t` samples in PROGMEM.
- Values are expected to be in the range `0–200`.
- `initialize()` and `fetchData()` succeed without hardware access.
- `getData()` returns `nullptr` until `fetchData()` has been called.
- `GraphGenerator` reads samples with `pgm_read_word()`.

Replace the placeholder/sample values in `HardcodedDataSource.h` when the production dataset is available. Keep the array length and `getDataLength()` consistent.

### `UARTDataSource`

`UARTDataSource.h` is a compile-safe future stub. It currently has:

```cpp
#define UART_DATASOURCE_ENABLED 0
```

Its constructor allocates an `int16_t` buffer, but initialization and acquisition intentionally return failure until the external IC protocol is defined and implemented.

To make UART acquisition active later, change the single source instantiation in `esp32_thermal_printer.ino` and implement the UART protocol in the data source. `GraphGenerator` and `ThermalPrinter` should not need to change.

## Graph rendering

`GraphGenerator` renders the curve as follows:

1. Allocates one processed sample per graph row.
2. Uses runtime max-pooling when the input contains at least as many samples as graph rows.
3. Constrains each sample to `0..Y_MAX`.
4. Applies an 11-sample moving average.
5. Maps load values horizontally across the 480-pixel graph width.
6. Connects consecutive rows with Bresenham line segments.

For the current configuration, 750 input samples are mapped onto 750 graph rows. The pooling branch remains in place so larger future UART datasets can be downsampled without changing the renderer.

### Bitmap invariants

- Keep `GRAPH_WIDTH` divisible by 8.
- Keep all drawing coordinates within the canvas.
- Read PROGMEM arrays with `pgm_read_byte()` or `pgm_read_word()`.
- Do not call `free()` on the pointer returned by `HardcodedDataSource`.
- Keep the graph area and canvas height consistent with the margin values.

## Printer output

The text portion currently prints:

1. `Standard Failure Graph` as a centered, double-height title.
2. A date/time line using the current placeholder literals in the sketch.
3. `Sample No.` as a blank operator-entry line.
4. `Load (kN)` centered immediately before the bitmap.
5. The graph bitmap.

The firmware resets the printer state before each text block and sends the bitmap in 512-byte chunks to reduce UART buffering problems.

## LED status

| LED color | State |
|---|---|
| Off/black | Idle |
| Light blue | Processing |
| Green | Print completed |
| Red | Failure |

## Serial diagnostics

Open the USB serial monitor at **115200 baud**. The sketch reports:

- Canvas dimensions and byte allocation
- Printer initialization and configuration
- Data-source initialization/fetch failures
- Graph-generation stages
- Bitmap transmission progress
- Print completion or failure

`PRINTER_DEBUG` is enabled in the main sketch. As a result, printer command bytes are logged to the USB serial monitor while ESC/POS commands are sent.

## Troubleshooting

### The printer does not respond

- Verify TX/RX are crossed correctly.
- Confirm the printer's electrical interface and use a TTL-to-RS232 converter if required.
- Confirm the printer is configured for 19200 baud, 8 data bits, no parity, and 1 stop bit.
- Check the printer power supply and common ground.
- Watch the USB serial log for initialization failures.

### The graph is clipped or shifted

- Keep `GRAPH_WIDTH` at a multiple of 8.
- Recheck `TOP_MARGIN`, `BOTTOM_MARGIN`, and `GRAPH_HEIGHT` together.
- Ensure grid spacing matches the number of axis divisions.
- Remember that canvas coordinates start at zero and the last valid row is `canvasHeight - 1`.

### The curve is flat or ends early

- Verify the data source returns the expected length.
- Confirm all production samples are present in the PROGMEM array.
- Keep values within `0..200`; out-of-range values are constrained during rendering.
- For a UART source, verify `fetchData()` succeeds before `getData()` is used.

### Canvas allocation fails

- Reduce `GRAPH_HEIGHT` only if the printed output can be shorter.
- Enable PSRAM in the board configuration where supported.
- Avoid allocating additional large buffers during graph generation.

### Text contains unexpected characters

- Confirm the printer is reset before a print job.
- Keep text commands separate from bitmap transmission.
- Check that the selected font size and line spacing fit the printer's printable width.
- Disable `PRINTER_DEBUG` only on the USB debug path if command logging is too noisy; do not remove printer commands.

## Development rules

- Treat `BitmapCanvas.h`, `ThermalPrinter.h`, and `Font5x7.h` as sealed unless a task specifically requires a change.
- Do not introduce STL containers, exceptions, or RTTI-dependent behavior into the firmware.
- Use fixed-width integer types for embedded data and coordinates.
- Preserve the `DataSource` boundary when adding new acquisition hardware.
- Validate firmware changes with the ESP32-S3 compile command before uploading to hardware.
