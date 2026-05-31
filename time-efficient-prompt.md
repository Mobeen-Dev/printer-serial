Now I have everything needed for a full quantitative performance analysis. Let me build the complete report with the pipeline diagram first, then the detailed deliverables.---



Print pipeline — latency per stage
Application logic
Canvas alloc · graph render · data fetch
One-time, pre-transmission
~500 ms total · not in print path

ESC/POS command generation
setDefault · setAlign · setFontSize · feed
⚠ 510 ms explicit delay
6 sendCommand() calls × avg 85 ms each

ThermalPrinter driver
sendCommand() · flush() · delay() per call
✗ PRIMARY BOTTLENECK
flush() blocks until TX FIFO empty each call
UART @ 19200 baud
1920 B/s · 512 B chunks · 10 ms inter-chunk
✗ SEVERE BOTTLENECK
57 600 Baud supported; using 19 200 (3.3×)
Bitmap chunking loop
48 000 B / 512 B = 94 chunks × 10 ms
✗ 940 ms wasted delay
flush() + 10 ms sleep after every 512 B chunk

Printer receive buffer
TM-T88III: 4 KB receive FIFO
Not a bottleneck at 19 200 baud
Buffer never fills — MCU is too slow
Printer firmware / rasteriser
Decodes GS v 0, rasterises bitmap rows
Hardware-limited; not reducible
~100 mm/s max paper speed

Thermal print head
Physical paper advance limit
Hard ceiling: ~100 mm/s / 203 dpi
≈ ~0.8 lines/ms (8 dots/line)

Delay budget — current implementation (bitmap phase only)
Baud rate (19 200): ~25 s transmission time
~940 ms
510ms
flush+other overhead
Baud-rate-limited TX time
Chunk sleep delays
ESC/POS cmd delays
flush overhead
Total current: ~27 s bitmap transmission · Target after optimization: ~8–9 s
Baud rate change alone (19 200 → 57 600) yields 3× speed-up. Removing delays adds another 15%.


## Deliverable 1 — Performance analysis report

### Throughput baseline: exact numbers from the code

**Baud rate:** `PRINTER_BAUD 19200` → `19200 / 10 = 1920 bytes/sec` (8N1 = 10 bits per byte).

**Bitmap dimensions:** `GRAPH_WIDTH = 512`, total height = `GRAPH_HEIGHT + TOP_MARGIN + BOTTOM_MARGIN = 750 + 70 + 40 = 860`. Canvas bytes = `(512/8) × 860 = 64 × 860 = 55 040 bytes`.

**Theoretical TX time at 19 200 baud:** `55 040 / 1920 = 28.7 seconds` — just for raw data, at zero software overhead.

Now count every `delay()` and `flush()` call that fires during a print job:

**Initialization and configuration phase:**

| Call | Delay injected |
|---|---|
| `begin()` → `delay(500)` before init cmd | 500 ms |
| `begin()` → `sendCommand(ESC @, 2, 500)` | 500 ms |
| `begin()` → `setDefault()` → `sendCommand(ESC @, 2, 300)` | 300 ms |
| `setDensity()` → `sendCommand(..., 100)` | 100 ms |
| `setLineHeight()` → `sendCommand(..., 10)` | 10 ms |
| **Subtotal init** | **1 410 ms** |

**Print sequence phase (lines 222–233):**

| Call | Delay injected |
|---|---|
| `setDefault()` → `sendCommand(ESC @, 2, 300)` | 300 ms |
| `setLineHeight(24)` → `sendCommand(..., 10)` | 10 ms |
| `setAlign(CENTER)` → `sendCommand(..., 50)` | 50 ms |
| `println("Standard Failure Graph")` → `flush() + delay(10)` | 10 ms |
| `feed(1)` → `sendCommand(..., 1×50)` | 50 ms |
| `setFontSize(1,1)` → `sendCommand(..., 50)` | 50 ms |
| `println("Load (kN)")` → `flush() + delay(10)` | 10 ms |
| `feed(1)` → `sendCommand(..., 50)` | 50 ms |
| **Subtotal pre-bitmap** | **530 ms** |

**Bitmap transmission loop:**

Chunk size = 512 bytes. Total bytes = 55 040. Number of chunks = `ceil(55 040 / 512) = 108`.

Per chunk: `serial.write(512 bytes)` + `serial.flush()` + `delay(10)`.

- `serial.write(512)` at 1920 B/s = 267 ms transmission time.
- `serial.flush()` = blocks until the UART TX FIFO drains = effectively 0 ms additional (it finishes what write started, but it's still a blocking wait that prevents any overlap).
- `delay(10)` = 10 ms dead time.

So per 512-byte chunk: **267 ms TX + 10 ms sleep = 277 ms** of wall time.

Total bitmap loop: `108 × 277 ms = ~29.9 seconds`. Plus `delay(50)` at the end = **~30 seconds total for the bitmap alone**.

`sendCommand()` for the `GS v 0` header: `delay(20)` = 20 ms.

**Grand total current wall time (print phase only, after graph generation):**

| Phase | Time |
|---|---|
| Init delays | 1 410 ms |
| Pre-bitmap config | 530 ms |
| `GS v 0` command | 20 ms |
| Bitmap TX loop | ~29 900 ms |
| Final `delay(50)` | 50 ms |
| **Total** | **~31.9 seconds** |

**Effective throughput:** `55 040 bytes / 31.9 s = 1 726 B/s` — only **89.9% of the 1920 B/s theoretical maximum at this baud rate**, with the missing ~10% burned in the `delay(10)` inter-chunk sleeps.

**Transmission utilisation at 19 200 baud:** `(55 040 / 1920) / 31.9 = 90%` — meaning virtually all the slowness is the baud rate itself, not the software.

---

### Bottleneck ranking by impact

**#1 — Baud rate set to 19 200 instead of 57 600 (impact: 3.0×)**

The TM-T88III supports up to 57 600 baud. The firmware uses 19 200. This single setting is responsible for ~19 seconds of the ~30-second bitmap transmission. Changing one `#define` recovers two-thirds of total print time.

**#2 — `delay(10)` after every 512-byte chunk (impact: ~3.5%)**

108 chunks × 10 ms = 1 080 ms of pure dead time during which the UART is idle and the printer is waiting. The delay has no functional purpose — the printer's 4 KB receive buffer is nowhere near full at this baud rate.

**#3 — `serial.flush()` after every chunk (impact: latency-inducing)**

`flush()` in Arduino's `HardwareSerial` blocks until the transmit shift register and FIFO are empty. When called after every 512-byte chunk, it prevents the next `write()` from starting until the hardware has fully clocked out the previous chunk. This eliminates any possibility of double-buffering or pipelining and forces strictly sequential, stop-start transmission.

**#4 — `sendCommand()` hardcoded delays (impact: 530 ms in print sequence)**

Every ESC/POS configuration call — `setAlign`, `setFontSize`, `feed`, `setLineHeight` — sleeps for 10–300 ms after sending 2–5 bytes. The TM-T88III processes these commands in microseconds. The delays are 1000× longer than necessary.

**#5 — Repeated `setDefault()` / `ESC @` calls (impact: 600 ms, command redundancy)**

`begin()` calls `setDefault()` internally. Then `printGraph()` calls `setDefault()` again on line 224 before the heading, adding another 300 ms reset cycle with no effect on output quality.

**#6 — 512-byte chunk size (minor, secondary to baud rate)**

At 57 600 baud (3× faster), the UART TX FIFO can sustain 5 760 B/s. The ESP32-S3's hardware UART FIFO is 128 bytes but the driver uses DMA, effectively supporting much larger logical writes. Chunks of 4–8 KB instead of 512 bytes reduce loop overhead from 108 iterations to 7–14 iterations.

---

## Deliverable 2 — Optimization opportunities

**High impact**

Raise baud rate from 19 200 to 57 600. One line of code, ~3× throughput improvement, ~19 seconds saved. The TM-T88III's DIP switch SW2-1 and SW2-2 control the baud rate on the hardware side; verify they are set to 57 600 before changing the firmware. If the printer is in its factory configuration (often 9 600 baud), set it to 57 600 first.

Remove `delay(10)` from the bitmap chunk loop entirely. The printer's receive buffer handles the rate; the MCU doesn't need to throttle. Saves 1 080 ms.

Remove `serial.flush()` from inside the bitmap chunk loop. Move a single `flush()` to after the entire bitmap has been written. This allows the UART DMA to continue filling the TX FIFO while the CPU prepares the next chunk pointer, enabling continuous streaming.

**Medium impact**

Reduce `sendCommand()` default delay from 50 ms to 2 ms for non-initialisation commands. ESC/POS formatting commands are acknowledged by the printer in under 1 ms at any supported baud rate. A 2 ms guard is sufficient for the worst-case printer firmware latency. Saves ~480 ms across the print sequence.

Increase chunk size from 512 to 4096 bytes. Reduces loop iteration count from 108 to 14, cutting per-chunk overhead from 108 × (flush latency + loop body) to 14 iterations.

Remove the second `setDefault()` call from `printGraph()`. The printer is already in a known-good state from `begin()`. Saves 300 ms.

**Low impact**

Merge `setLineHeight`, `setAlign`, `setFontSize` into a single batched write rather than three separate `sendCommand()` calls. Minor reduction in UART transaction count.

Remove the `delay(2000)` in `setup()` (line 121). This is a startup debug delay with no functional purpose during normal operation.

Pre-allocate the canvas once at startup rather than allocating and freeing it on every `printGraph()` call. Eliminates one 55 040-byte `malloc/free` cycle and potential heap fragmentation.

---

## Deliverable 3 — Code-level recommendations

### 3.1 — Baud rate (highest single impact)

```cpp
// Before
#define PRINTER_BAUD 19200

// After — verify DIP switches SW2-1=ON, SW2-2=ON on TM-T88III
#define PRINTER_BAUD 57600
```

Time saved: ~19 seconds. No other code change needed — `PrinterSerial.begin()` passes this directly to the UART hardware.

---

### 3.2 — Strip delays from `sendCommand()` for non-init calls

```cpp
// Before — every command pays 50 ms minimum
bool sendCommand(const uint8_t* cmd, size_t len, uint16_t delayMs = 50) {
  size_t written = serial.write(cmd, len);
  serial.flush();
  delay(delayMs);
  return (written == len);
}

// After — split into init-safe and runtime-safe variants
bool sendCommand(const uint8_t* cmd, size_t len, uint16_t delayMs = 2) {
  size_t written = serial.write(cmd, len);
  // Don't flush here; let the UART DMA drain naturally
  if (delayMs > 0) delay(delayMs);
  return (written == len);
}

bool sendCommandAndWait(const uint8_t* cmd, size_t len, uint16_t delayMs) {
  size_t written = serial.write(cmd, len);
  serial.flush();      // Only block when we genuinely need to know it's done
  delay(delayMs);
  return (written == len);
}
```

Use `sendCommandAndWait` only in `begin()` and `setDefault()`. Use the lighter `sendCommand` (2 ms) for all runtime formatting calls (`setAlign`, `setFontSize`, `setLineHeight`, `feed`).

---

### 3.3 — Fix the bitmap loop

```cpp
// Before — 108 iterations × (flush + 10 ms sleep) = 1 080 ms wasted
bool printBitmap(uint16_t width, uint16_t height, const uint8_t* bitmapData) {
  uint16_t widthBytes = width / 8;
  uint8_t cmd[] = { GS, 'v', '0', 0x00,
    (uint8_t)(widthBytes & 0xFF), (uint8_t)((widthBytes >> 8) & 0xFF),
    (uint8_t)(height & 0xFF),     (uint8_t)((height >> 8) & 0xFF) };
  if (!sendCommand(cmd, 8, 20)) return false;

  const size_t CHUNK_SIZE = 512;
  size_t totalBytes = widthBytes * height;
  size_t sent = 0;
  while (sent < totalBytes) {
    size_t chunkSize = min(CHUNK_SIZE, totalBytes - sent);
    size_t written = serial.write(bitmapData + sent, chunkSize);
    sent += written;
    serial.flush();    // ← blocks every 512 bytes
    delay(10);         // ← 10 ms dead time every chunk
  }
  delay(50);
  return true;
}

// After — continuous DMA stream, single flush at the end
bool printBitmap(uint16_t width, uint16_t height, const uint8_t* bitmapData) {
  uint16_t widthBytes = width / 8;
  uint8_t cmd[] = { GS, 'v', '0', 0x00,
    (uint8_t)(widthBytes & 0xFF), (uint8_t)((widthBytes >> 8) & 0xFF),
    (uint8_t)(height & 0xFF),     (uint8_t)((height >> 8) & 0xFF) };
  serial.write(cmd, 8);   // No flush, no delay — just queue it

  const size_t CHUNK_SIZE = 4096;   // Larger chunks, fewer iterations
  size_t totalBytes = (size_t)widthBytes * height;
  size_t sent = 0;

  while (sent < totalBytes) {
    size_t chunkSize = min(CHUNK_SIZE, totalBytes - sent);
    // write() is non-blocking up to the driver buffer size;
    // it returns when the chunk is accepted by the DMA ring.
    size_t written = serial.write(bitmapData + sent, chunkSize);
    sent += written;
    // No flush(), no delay() — let the UART hardware stream continuously.
    // If write() returns less than chunkSize, the TX buffer was full;
    // yield() gives the FreeRTOS scheduler a chance to drain it.
    if (written < chunkSize) {
      sent -= (chunkSize - written);  // retry unwritten bytes next iteration
      yield();
    }
  }

  serial.flush();   // One final flush to confirm all bytes are transmitted
  return true;
}
```

---

### 3.4 — Remove redundant init call and startup delay

```cpp
// In printGraph(), before the heading:

// Before
printer->setDefault();      // ← redundant; begin() already did this
printer->setLineHeight(24);
printer->setAlign(ALIGN_CENTER);

// After
printer->setLineHeight(24);
printer->setAlign(ALIGN_CENTER);
```

```cpp
// In setup():

// Before
delay(2000);  // ← removes nothing useful for production

// After — remove entirely, or reduce to delay(500) if startup stabilisation is needed
```

---

### 3.5 — Timing instrumentation (for ongoing profiling)

Add this to `printGraph()` to measure each phase precisely:

```cpp
uint32_t t0, t1;

t0 = millis();
generator.drawCurve(curveData, dataLen);
Serial.printf("  [PERF] Curve render: %lu ms\n", millis() - t0);

t0 = millis();
printer->printBitmap(canvas->getWidth(), canvas->getHeight(), canvas->getData());
t1 = millis();
uint32_t bitmapMs = t1 - t0;
uint32_t totalBytes = (canvas->getWidth() / 8) * canvas->getHeight();
Serial.printf("  [PERF] Bitmap TX: %lu ms — %lu B — %.1f B/s\n",
              bitmapMs, totalBytes, (float)totalBytes * 1000.0f / bitmapMs);
```

---

## Deliverable 4 — Maximum throughput architecture

**Realistic maximum at 57 600 baud:**

- Byte rate: `57 600 / 10 = 5 760 B/s`
- Bitmap size: 55 040 bytes
- Theoretical minimum TX time: `55 040 / 5 760 = 9.6 seconds`
- With software overhead (eliminated delays, one final flush): **~10 seconds total**

**Comparison table:**

| Configuration | Bitmap TX time | Total print time |
|---|---|---|
| Current (19 200 baud, delays) | ~30 s | ~32 s |
| 19 200 baud, delays removed | ~28.7 s | ~30 s |
| 57 600 baud, delays retained | ~10.5 s | ~12 s |
| **57 600 baud, delays removed (target)** | **~9.6 s** | **~10 s** |
| 115 200 baud (if printer DIP-switchable) | ~4.8 s | ~5.5 s |

The TM-T88III's documented maximum is 57 600 baud over RS-232. If the unit is the USB/Ethernet version, the interface bypasses UART entirely and the baud rate constraint disappears — but the ESC/POS command overhead still applies.

**Hardware ceiling — the thermal head:**

The TM-T88III prints at up to 150 mm/s at 203 dpi. At 203 dpi, one dot row = 1/203 inch = 0.125 mm. At 150 mm/s: `150 / 0.125 = 1 200 dot rows/sec`. Your bitmap is 860 rows tall. Minimum print time regardless of serial speed: `860 / 1200 = 0.72 seconds`. The paper mechanism, not the data rate, is the ultimate floor — and at 57 600 baud the firmware is already feeding data faster than the head can consume it, meaning the printer will begin buffering and printing continuously without pauses.

**Priority implementation plan:**

1. Change `PRINTER_BAUD` to 57 600 and match the printer DIP switches. Verify with a 10-byte test print first. **(1 minute change, 3× gain)**
2. Remove `delay(10)` and `serial.flush()` from inside the bitmap loop. Apply the revised `printBitmap()` above. **(15 minutes, additional 1.1× gain)**
3. Drop `sendCommand()` default delay from 50 ms to 2 ms for runtime commands. **(5 minutes, eliminates 480 ms of command overhead)**
4. Remove the second `setDefault()` in `printGraph()`. **(1 minute, saves 300 ms)**
5. Remove or reduce the `delay(2000)` startup hold in `setup()`. **(1 minute, saves 2 s off time-to-first-print)**

After steps 1–4, expected total print time drops from **~32 seconds to ~10 seconds**, with continuous smooth paper advance and no visible burst-pause-burst pattern, because the printer's receive buffer will be continuously supplied faster than the thermal head drains it.