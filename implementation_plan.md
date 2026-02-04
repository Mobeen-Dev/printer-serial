# Analysis & Implementation Plan: ESP32-C3 Deployment

## 1. Project Goal
Deploy the functionality of [grid_test8.py](file:///c:/DRIVE_D/PythonProject/printer-serial/grid_test8.py) (receiving 4800 data points and printing a high-res bitmap graph) onto an **ESP32-C3-mini**.

## 2. Hardware Suitability Analysis (ESP32-C3)

### **The Verdict: VIABLE but requires optimization.**

The ESP32-C3 is a capable RISC-V microcontroller, but it has tighter resource constraints compared to the ESP32-S3 or original ESP32.

### **Good Points (Pros)**
*   **Cost Effective**: ideal for production scaling.
*   **Processing Power**: 160MHz is more than enough for generating the graph geometry.
*   **Connectivity**: Native USB-Serial (JTAG) allows easy debugging while keeping hardware UARTs free.
*   **Peripherals**: Has 2 hardware UARTs (U0, U1). You can use:
    *   **USB Port**: Debugging/Programming.
    *   **UART1**: Communication with the Printer.
    *   **UART0**: Receiving 4800 points from the external controller.

### **Bad Points (Cons & Risks)**
*   **Memory (RAM) Constraints**: this is the critical bottleneck.
    *   **Current Bitmap Size**: 512 pixels width × 1270 pixels height = **~81,280 bytes (80 KB)**.
    *   **Data Size**: 4800 points × 4 bytes (float) = **~19 KB**.
    *   **Total Static RAM Requirement**: ~100 KB + Stack + Heap overhead.
    *   **The Problem**: The ESP32-C3 has 400KB SRAM, but available heap for Python (MicroPython) is often < 150KB. Allocating a single contiguous 80KB block for the bitmap might fail or cause instability due to fragmentation.
*   **Printing Speed (Bottleneck)**:
    *   Current code uses `baudrate=19200`.
    *   Transmitting 81KB at 19200 baud takes **~42 seconds**. This is very slow for production.
    *   *Mitigation*: We MUST check if the printer supports `115200` or `38400`.

## 3. Implementation Strategy

### **Option A: Optimized MicroPython (Recommended for Ease of Dev)**
To avoid Out-Of-Memory (OOM) errors, we cannot create the entire 80KB image in memory at once.
*   **Strategy**: **"Banded" or "Scanline" Rendering.**
    1.  Receive and store all 4800 points (19KB is safe).
    2.  Process the graph in chunks (e.g., 50 lines at a time).
    3.  Draw the grid/labels/curve for just those 50 lines.
    4.  Send those lines to the printer.
    5.  Clear buffer and repeat.
*   **Result**: Reduces RAM usage from 80KB -> ~4KB. Very safe for ESP32-C3.

### **Option B: C++ / Arduino Framework (Recommended for Stability)**
*   C++ uses memory much more efficiently than Python.
*   The 100KB static allocation is trivial for an ESP32-C3 in C++.
*   **Pros**: Robust, fast, no garbage collection pauses.
*   **Cons**: Longer development time to port the Python logic to C++.

## 4. Proposed Workflow "Batch Printing"

1.  **Idle State**: ESP32 waits for "Start" signal or data stream on UART RX.
2.  **Data Ingestion**:
    *   Read 4800 values (Comma Separated or Binary).
    *   Store in `float raw_data[4800]`.
3.  **Data Processing**:
    *   Apply scaling (0-200K range).
    *   Compute build-up curve statistics (if needed).
4.  **Printing Phase**:
    *   Initialize Printer (Wake up).
    *   **Header**: Print text metadata.
    *   **Graph Loop**:
        *   `for y in range(0, HEIGHT, chunk_size)`:
            *   Render chunk `y` to `y + chunk_size`.
            *   Send `GS v 0` command for this chunk.
    *   **Footer**: Print validation text.
    *   Cut Paper.

## 5. Next Steps Plan

- [ ] **Verify Printer Baud Rate**: Can we bump `19200` to `115200`? This saves ~30 seconds per print.
- [ ] **Define Data Protocol**: How does the controller send 4800 points? (JSON? CSV? Binary raw floats?). Binary is preferred for speed.
- [ ] **Develop MVP on ESP32**: Port the [BitmapCanvas](file:///c:/DRIVE_D/PythonProject/printer-serial/grid_test8.py#132-337) logic to a memory-efficient class.
