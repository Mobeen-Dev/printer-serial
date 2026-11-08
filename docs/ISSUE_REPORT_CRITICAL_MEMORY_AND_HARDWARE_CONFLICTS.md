# Bug Report: Critical Heap Overflow, ESP32-S3 USB Hardware Conflict & Task Stack Pressure

## Description
During a deep code audit of the native ESP-IDF thermal printer application, three critical and high-severity issues were identified:

1. **`BitmapCanvas` Heap Memory Corruption:**
   `CANVAS_WIDTH` was configured as `558` (not a multiple of 8). `bytesPerLine` was calculated as `558 / 8 = 69` bytes (truncated), allocating 59,340 bytes. Drawing pixels at $x \ge 552$ on line $y = 859$ resulted in `byteIndex = 59,340`, writing out-of-bounds into the heap allocator metadata and causing heap panics (`multi_heap.c: corrupt heap`).

2. **ESP32-S3 Hardware Pin Conflict on GPIO 19 & 20:**
   The PIC UART acquisition was assigned to `GPIO_NUM_19` (RX) and `GPIO_NUM_20` (TX). On the ESP32-S3, these pins are hardwired to the internal USB controller (`USB_D-` and `USB_D+`). With USB-Serial-JTAG enabled in `sdkconfig`, plugging into native USB caused communication failures and disconnection.

3. **Idle Heap Lock in `printGraph()`:**
   The ~60 KB canvas frame buffer was allocated before calling `dataSource->fetchData()`, which blocks indefinitely on `pic_data_queue`. On ESP32-S3 without PSRAM, this locked 60 KB of contiguous internal SRAM while waiting for sensor data.

4. **FreeRTOS Stack Overflow Risk:**
   `pic_packet_t pkt` (1,602 bytes) was allocated as a local variable inside `PICDataSource::fetchData()`. Calling this from tasks with 4 KB stacks caused severe stack pressure.

---

## Resolution
- Aligned `CANVAS_WIDTH` to `560` ($512 + 32 + 16$) and computed `bytesPerLine = (width + 7) / 8`.
- Reassigned PIC UART to safe general-purpose GPIOs: **GPIO 4 (RX)** and **GPIO 5 (TX)**.
- Re-architected `printGraph()` to fetch data first, allocating the 60 KB canvas only when valid data is ready and freeing it immediately after printing.
- Moved `pic_packet_t` into `PICDataSource` heap member `_rxPacket`, eliminating 1.6 KB from task stacks.
- Replaced non-standard `itoa` with `snprintf` in `GraphGenerator.cpp`.
