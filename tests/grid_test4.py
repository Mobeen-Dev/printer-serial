#!/usr/bin/env python3
"""
Epson TM-T88III (80mm) - Distribution with Embedded Axis Labels
Axis labels are drawn INTO the bitmap itself as pixel text
"""

import serial
import time
import math

# === ESC/POS Commands ===
ESC = b"\x1b"
GS = b"\x1d"

# === Adjustable parameters ===
WIDTH = 512  # 80mm printer width
HEIGHT = 1200  # Paper length
GRID_X_SPACING = 80  # X-axis spacing (2 time units per division)
GRID_Y_SPACING = 55  # Y-axis spacing (25K pressure per division)
GRID_DASHED = True

# Axis ranges
X_MAX = 30  # Time: 0 to 30
X_STEP = 2  # Step: 2
Y_MAX = 200  # Pressure: 0 to 200K
Y_STEP = 25  # Step: 25K

# Margins for labels
LEFT_MARGIN = 50  # Space for Y-axis labels on left
RIGHT_MARGIN = 50  # Space for Y-axis labels on right
BOTTOM_MARGIN = 30  # Space for X-axis labels at bottom

# Adjusted dimensions
GRAPH_WIDTH = WIDTH - LEFT_MARGIN - RIGHT_MARGIN
GRAPH_START_X = LEFT_MARGIN
# ==============================


class EpsonThermalPrinter:
    def __init__(self, port="COM7", baudrate=19200):
        """Initialize the printer connection"""
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3,
            xonxoff=True,
            rtscts=False,
            dsrdtr=False,
            write_timeout=3,
        )

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.5)

        self.begin()
        self.set_default()

    def begin(self):
        self.ser.write(ESC + b"@")
        time.sleep(0.5)

    def set_default(self):
        self.ser.write(ESC + b"@")
        time.sleep(0.3)

    def set_print_density(self, density=8, breakTime=2):
        printSetting = (density << 4) | breakTime
        self.ser.write(bytes([0x12, 0x23, printSetting]))
        time.sleep(0.1)

    def set_line_height(self, val=32):
        if val < 24:
            val = 24
        self.ser.write(ESC + b"3" + bytes([val]))
        time.sleep(0.1)

    def println(self, text=""):
        self.ser.write(text.encode("ascii", errors="replace") + b"\n")
        time.sleep(0.1)

    def set_align(self, align="left"):
        align_codes = {"left": 0, "center": 1, "right": 2}
        code = align_codes.get(align, 0)
        self.ser.write(ESC + b"a" + bytes([code]))
        time.sleep(0.05)

    def set_font_size(self, width=1, height=1):
        if width < 1:
            width = 1
        if width > 8:
            width = 8
        if height < 1:
            height = 1
        if height > 8:
            height = 8

        size = ((width - 1) << 4) | (height - 1)
        self.ser.write(GS + b"!" + bytes([size]))
        time.sleep(0.05)

    def print_bitmap(self, width, height, bitmap_data):
        width_bytes = width // 8

        cmd = GS + b"v0"
        cmd += bytes([0])
        cmd += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])
        cmd += bytes([height & 0xFF, (height >> 8) & 0xFF])

        self.ser.write(cmd)

        chunk_size = 4096
        for i in range(0, len(bitmap_data), chunk_size):
            chunk = bitmap_data[i : i + chunk_size]
            self.ser.write(chunk)

        time.sleep(0.2)

    def feed(self, lines=1):
        self.ser.write(ESC + b"d" + bytes([lines]))
        time.sleep(lines * 0.1)

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()


class BitmapCanvas:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.bytes_per_line = width // 8
        self.data = bytearray(self.bytes_per_line * height)

    def clear(self):
        self.data = bytearray(self.bytes_per_line * self.height)

    def set_pixel(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        byte_index = (x // 8) + y * self.bytes_per_line
        bit_position = x & 7
        self.data[byte_index] |= 0x80 >> bit_position

    def draw_vertical_line(self, x, y_start=0, y_end=None, dashed=False):
        if y_end is None:
            y_end = self.height
        for y in range(y_start, y_end):
            if not dashed or (y // 4) % 2 == 0:
                self.set_pixel(x, y)

    def draw_horizontal_line(self, y, x_start=0, x_end=None, dashed=False):
        if x_end is None:
            x_end = self.width
        for x in range(x_start, x_end):
            if not dashed or (x // 4) % 2 == 0:
                self.set_pixel(x, y)

    def draw_char(self, char, x, y, size=1):
        """Draw a simple character (numbers 0-9, K)"""
        # Simple 5x7 font for numbers
        font = {
            "0": [
                [0, 1, 1, 1, 0],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0],
            ],
            "1": [
                [0, 0, 1, 0, 0],
                [0, 1, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 1, 1, 1, 0],
            ],
            "2": [
                [0, 1, 1, 1, 0],
                [1, 0, 0, 0, 1],
                [0, 0, 0, 0, 1],
                [0, 0, 0, 1, 0],
                [0, 0, 1, 0, 0],
                [0, 1, 0, 0, 0],
                [1, 1, 1, 1, 1],
            ],
            "3": [
                [0, 1, 1, 1, 0],
                [1, 0, 0, 0, 1],
                [0, 0, 0, 0, 1],
                [0, 0, 1, 1, 0],
                [0, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0],
            ],
            "4": [
                [0, 0, 0, 1, 0],
                [0, 0, 1, 1, 0],
                [0, 1, 0, 1, 0],
                [1, 0, 0, 1, 0],
                [1, 1, 1, 1, 1],
                [0, 0, 0, 1, 0],
                [0, 0, 0, 1, 0],
            ],
            "5": [
                [1, 1, 1, 1, 1],
                [1, 0, 0, 0, 0],
                [1, 1, 1, 1, 0],
                [0, 0, 0, 0, 1],
                [0, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0],
            ],
            "6": [
                [0, 1, 1, 1, 0],
                [1, 0, 0, 0, 0],
                [1, 0, 0, 0, 0],
                [1, 1, 1, 1, 0],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0],
            ],
            "7": [
                [1, 1, 1, 1, 1],
                [0, 0, 0, 0, 1],
                [0, 0, 0, 1, 0],
                [0, 0, 1, 0, 0],
                [0, 1, 0, 0, 0],
                [0, 1, 0, 0, 0],
                [0, 1, 0, 0, 0],
            ],
            "8": [
                [0, 1, 1, 1, 0],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0],
            ],
            "9": [
                [0, 1, 1, 1, 0],
                [1, 0, 0, 0, 1],
                [1, 0, 0, 0, 1],
                [0, 1, 1, 1, 1],
                [0, 0, 0, 0, 1],
                [0, 0, 0, 0, 1],
                [0, 1, 1, 1, 0],
            ],
            "K": [
                [1, 0, 0, 0, 1],
                [1, 0, 0, 1, 0],
                [1, 0, 1, 0, 0],
                [1, 1, 0, 0, 0],
                [1, 0, 1, 0, 0],
                [1, 0, 0, 1, 0],
                [1, 0, 0, 0, 1],
            ],
        }

        if char not in font:
            return

        pattern = font[char]
        for row_idx, row in enumerate(pattern):
            for col_idx, pixel in enumerate(row):
                if pixel:
                    px = x + col_idx * size
                    py = y + row_idx * size
                    for sy in range(size):
                        for sx in range(size):
                            self.set_pixel(px + sx, py + sy)

    def draw_text(self, text, x, y, size=1):
        """Draw text string"""
        offset = 0
        for char in text:
            self.draw_char(char, x + offset, y, size)
            offset += 6 * size  # 5 pixels + 1 space

    def draw_thick_point(self, x, y, thickness=2):
        for dy in range(-1, 2):
            for dx in range(-thickness, thickness + 1):
                self.set_pixel(x + dx, y + dy)


def skewed_gaussian(x, mu, sigma, alpha):
    z = (x - mu) / sigma
    base = math.exp(-0.5 * z * z)
    skew = 1.0 - alpha * (x - mu)
    if skew < 0:
        skew = 0
    return base * skew


def create_complete_graph():
    """Create complete graph with embedded labels"""
    canvas = BitmapCanvas(WIDTH, HEIGHT + BOTTOM_MARGIN)
    canvas.clear()

    # Draw Y-axis labels (Pressure - across the width)
    num_y_div = int(Y_MAX / Y_STEP)
    for i in range(num_y_div + 1):
        x_pos = GRAPH_START_X + i * GRID_Y_SPACING
        value = i * Y_STEP

        # Draw label at top
        if value == 0:
            canvas.draw_text("0", x_pos - 3, 5, 1)
        else:
            label = f"{value}"
            canvas.draw_text(label, x_pos - 8, 5, 1)
            if i < num_y_div:  # Don't draw K on last one if space issue
                canvas.draw_char("K", x_pos + len(label) * 6 - 8, 5, 1)

    # Draw grid in graph area
    for i in range(int(X_MAX / X_STEP) + 1):
        y_pos = 20 + i * GRID_X_SPACING
        if y_pos < HEIGHT:
            canvas.draw_horizontal_line(
                y_pos, GRAPH_START_X, GRAPH_START_X + GRAPH_WIDTH, GRID_DASHED
            )

    for i in range(num_y_div + 1):
        x_pos = GRAPH_START_X + i * GRID_Y_SPACING
        canvas.draw_vertical_line(x_pos, 20, HEIGHT, GRID_DASHED)

    # Draw X-axis labels (Time - down the height)
    for i in range(int(X_MAX / X_STEP) + 1):
        y_pos = 20 + i * GRID_X_SPACING
        value = i * X_STEP
        if y_pos < HEIGHT - 10:
            # Draw label on left margin
            label = str(value)
            canvas.draw_text(label, 5, y_pos - 3, 2)

    # Draw distribution curve
    values = []
    max_val = 0.0

    MU = 0.35
    SIGMA = 0.15
    ALPHA = 1.2
    AMPLIFY = 1.5

    for y in range(20, HEIGHT):
        yf = (y - 20) / (HEIGHT - 20 - 1)
        v = skewed_gaussian(yf, MU, SIGMA, ALPHA)
        v *= AMPLIFY
        values.append(v)
        if v > max_val:
            max_val = v

    if max_val < 1e-6:
        max_val = 1.0

    for idx, y in enumerate(range(20, HEIGHT)):
        n = values[idx] / max_val
        center_x = GRAPH_START_X + GRAPH_WIDTH // 2
        extent = int(n * (GRAPH_WIDTH // 2 - 10))

        x = center_x + extent
        canvas.draw_thick_point(x, y, 2)

    # Draw center baseline
    center_x = GRAPH_START_X + GRAPH_WIDTH // 2
    for y in range(20, HEIGHT, 2):
        canvas.set_pixel(center_x, y)

    # Draw axis titles at bottom
    canvas.draw_text("TIME", WIDTH // 2 - 20, HEIGHT + 10, 1)

    return canvas


def main():
    print("Epson TM-T88III - Distribution with Embedded Labels")
    print("=" * 60)
    print("Configuration:")
    print(f"  Canvas: {WIDTH}×{HEIGHT + BOTTOM_MARGIN} pixels")
    print(f"  Graph area: {GRAPH_WIDTH}×{HEIGHT - 20} pixels")
    print(f"  X-axis: 0 to {X_MAX} (step {X_STEP})")
    print(f"  Y-axis: 0 to {Y_MAX}K (step {Y_STEP}K)")
    print("=" * 60)

    print("\n[1/4] Connecting to printer...")
    try:
        printer = EpsonThermalPrinter(port="COM7", baudrate=19200)
        print("      ✓ Connected")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return

    try:
        print("\n[2/4] Configuring printer...")
        printer.set_print_density(10)
        printer.set_line_height(24)
        print("      ✓ Configuration applied")

        print("\n[3/4] Creating graph with embedded labels...")
        canvas = create_complete_graph()
        print(f"      ✓ Graph created: {canvas.width}×{canvas.height} pixels")

        print("\n[4/4] Printing to device...")
        printer.set_align("center")
        printer.set_font_size(2, 2)
        printer.println("Distribution Graph")
        printer.set_font_size(1, 1)
        printer.println("")

        printer.print_bitmap(canvas.width, canvas.height, canvas.data)
        print("      ✓ Bitmap printed")

        printer.feed(2)
        printer.set_font_size(2, 2)
        printer.set_align("center")
        printer.println("PRESSURE")
        printer.feed(10)

        print("\n" + "=" * 60)
        print("✓✓✓ PRINTING COMPLETED! ✓✓✓")
        print("=" * 60)
        print("\nOutput structure:")
        print("  ├─ Title")
        print("  ├─ Y-axis labels at top: 0  25  50K  75K... 200K")
        print("  ├─ X-axis labels on left: 0, 2, 4, 6... 30")
        print("  ├─ Continuous grid with distribution")
        print("  ├─ 'TIME' label at bottom")
        print("  └─ 'PRESSURE' title at end")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        printer.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()
