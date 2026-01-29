#!/usr/bin/env python3
"""
Epson TM-T88III (80mm) - Distribution with Build-up Curve
Updated to use build-up/drop/recovery pattern instead of hardcoded distribution
"""

import serial
import time
import random

# === ESC/POS Commands ===
ESC = b"\x1b"
GS = b"\x1d"

# === Adjustable parameters ===
WIDTH = 512  # 80mm printer width
HEIGHT = 1200  # Graph length
GRID_X_SPACING = 80  # X-axis spacing (space per time division)
GRID_Y_SPACING = 60  # Y-axis spacing (space per pressure division)
GRID_DASHED = True

# Axis ranges
X_MAX = 30  # Time: 0 to 30
X_STEP = 2  # Step: 2
Y_MAX = 200  # Pressure: 0 to 200K
Y_STEP = 25  # Step: 25K

# Margins for labels
LEFT_MARGIN = 30  # Space for X-axis labels on left
TOP_MARGIN = 70  # Space for Y-axis labels at top
BOTTOM_MARGIN = 10  # Space for bottom text

# Adjusted dimensions
HEIGHT = HEIGHT + TOP_MARGIN  # Bit-map length for y-axis label + graph area
GRAPH_WIDTH = int(GRID_Y_SPACING * (Y_MAX / Y_STEP))
GRAPH_START_X = LEFT_MARGIN  # Grid starts Above the X-axis labels
GRAPH_START_Y = TOP_MARGIN  # Grid starts BELOW the Y-axis labels
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
        time.sleep(0.01)

    def println(self, text=""):
        self.ser.write(text.encode("ascii", errors="replace") + b"\n")
        time.sleep(0.01)

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

        time.sleep(0.02)

    def feed(self, lines=1):
        self.ser.write(ESC + b"d" + bytes([lines]))

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

    def draw_char(self, char, x, y, size=1, rotate_90=False):
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

        if rotate_90:
            # Rotate 90° clockwise: (col, row) -> (height - 1 - row, col)
            char_height = len(pattern)  # 7
            char_width = len(pattern[0])  # 5
            for row_idx, row in enumerate(pattern):
                for col_idx, pixel in enumerate(row):
                    if pixel:
                        # 90° clockwise rotation
                        px = x + (char_height - 1 - row_idx) * size
                        py = y + col_idx * size
                        for sy in range(size):
                            for sx in range(size):
                                self.set_pixel(px + sx, py + sy)
        else:
            # Normal horizontal text
            for row_idx, row in enumerate(pattern):
                for col_idx, pixel in enumerate(row):
                    if pixel:
                        px = x + col_idx * size
                        py = y + row_idx * size
                        for sy in range(size):
                            for sx in range(size):
                                self.set_pixel(px + sx, py + sy)

    def draw_text(self, text, x, y, size=1, rotate_90=False):
        """Draw text string"""
        offset = 0
        for char in text:
            self.draw_char(char, x, y + offset, size, rotate_90)
            if rotate_90:
                offset += 8 * size  # Character height + spacing when rotated
            else:
                offset += 6 * size  # Character width + spacing when horizontal

    def draw_thick_point(self, x, y, thickness=2):
        for dy in range(-1, 2):
            for dx in range(-thickness, thickness + 1):
                self.set_pixel(x + dx, y + dy)

    def draw_line(self, x0, y0, x1, y1):
        """Draw line using Bresenham's algorithm"""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            self.set_pixel(x0, y0)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy


def generate_sample_data(num_points=4800):
    """Generate build-up/drop/recovery pattern data"""
    data = []
    cycle_len = num_points

    for c in range(1):
        # 1️⃣ Build-up curve
        for i in range(int(cycle_len * 0.4)):
            p = i / (cycle_len * 0.4)
            val = 150 * (p**2) + random.uniform(-5, 5)
            data.append(max(0, val))

        # 2️⃣ Sudden drop (brick break)
        data.append(5)

        # 3️⃣ Recovery tail
        remaining = cycle_len - len(data) % cycle_len
        for i in range(remaining):
            p = i / remaining
            val = 40 * (1 - p) + random.uniform(-3, 3)
            data.append(max(0, val))

    return data[:num_points]


def moving_average(data, window=5):
    """Apply moving average smoothing"""
    if window < 2:
        return data[:]

    half = window // 2
    out = []

    for i in range(len(data)):
        s = 0
        c = 0
        for j in range(i - half, i + half + 1):
            if 0 <= j < len(data):
                s += data[j]
                c += 1
        out.append(s / c)

    return out


def generate_graph_points(data, graph_width=480, graph_height=1200, margin=10):
    """Convert raw data to graph points with downsampling and scaling"""
    if not data:
        raise ValueError("Empty data")

    # --- Downsample to graph_height points using max pooling ---
    if len(data) > graph_height:
        ratio = len(data) / graph_height
        reduced = []
        for i in range(graph_height):
            start = int(i * ratio)
            end = int((i + 1) * ratio)
            segment = data[start:end]
            reduced.append(max(segment) if segment else data[start])

        # Apply smoothing
        data = moving_average(reduced, window=11)
    # Pad if smaller
    elif len(data) < graph_height:
        data = data + [0] * (graph_height - len(data))

    # --- Scaling ---
    dmin = min(data)
    dmax = max(data)
    center_x = graph_width // 2

    if dmax - dmin == 0:
        scale = 0
    else:
        scale = (graph_width // 2 - margin) / (dmax - dmin)

    # --- Convert to pixel points ---
    points = []
    for y in range(graph_height):
        val = data[y]
        extent = int((val - dmin) * scale)
        x = center_x + extent
        points.append((x, y))

    return points


def create_complete_graph():
    """Create complete graph with embedded labels and build-up curve"""
    canvas = BitmapCanvas(WIDTH, HEIGHT + BOTTOM_MARGIN)
    canvas.clear()

    # STEP 1: Draw Y-axis labels FIRST at the top (Pressure - across the width)
    num_y_div = int(Y_MAX / Y_STEP)
    for i in range(num_y_div + 1):
        x_pos = GRAPH_START_X + i * GRID_Y_SPACING
        value = i * Y_STEP

        if value != 0:
            label = f"{value}K"
            canvas.draw_text(label, x_pos - 13, 5, 2, rotate_90=True)

    # STEP 2: Draw grid BELOW the Y-axis labels (starting at GRAPH_START_Y)
    # Horizontal lines (time divisions)
    for i in range(int(X_MAX / X_STEP) + 1):
        y_pos = GRAPH_START_Y + i * GRID_X_SPACING
        if y_pos < HEIGHT:
            canvas.draw_horizontal_line(
                y_pos, GRAPH_START_X, GRAPH_START_X + GRAPH_WIDTH, GRID_DASHED
            )

    # Vertical lines (pressure divisions)
    for i in range(num_y_div + 1):
        x_pos = GRAPH_START_X + i * GRID_Y_SPACING
        canvas.draw_vertical_line(x_pos, GRAPH_START_Y, HEIGHT, GRID_DASHED)

    # STEP 3: Draw X-axis labels (Time - down the height)
    # Labels are rotated 90° clockwise and read vertically
    for i in range(int(X_MAX / X_STEP) + 1):
        y_pos = GRAPH_START_Y + i * GRID_X_SPACING
        value = i * X_STEP
        if y_pos < HEIGHT - 10:
            # Draw rotated label on left margin
            label = str(value)
            canvas.draw_text(label, 10, y_pos - 3, 2, rotate_90=True)

    # STEP 4: Generate and draw build-up curve
    print("      → Generating sample data...")
    raw_data = generate_sample_data(num_points=4800)

    print("      → Converting to graph points...")
    graph_height = HEIGHT - GRAPH_START_Y
    points = generate_graph_points(raw_data, GRAPH_WIDTH, graph_height, margin=10)

    print(f"      → Drawing curve with {len(points)} points...")
    # Draw the curve using line segments
    if points:
        prev_x, prev_y = points[0]
        prev_y += GRAPH_START_Y  # Offset to start below labels

        for x, y in points[1:]:
            y += GRAPH_START_Y  # Offset to start below labels
            canvas.draw_line(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y

    # Draw axis title at bottom
    canvas.draw_text("TIME", WIDTH // 2 - 15, HEIGHT + 5, 1, rotate_90=True)

    return canvas


def main():
    print("Epson TM-T88III - Build-up Curve Pattern")
    print("=" * 60)
    print("Configuration:")
    print(f"  Canvas: {WIDTH}×{HEIGHT + BOTTOM_MARGIN} pixels")
    print(f"  TOP_MARGIN: {TOP_MARGIN}px (Y-axis labels space)")
    print(f"  Graph starts at Y: {GRAPH_START_Y}px")
    print(f"  Graph area: {GRAPH_WIDTH}×{HEIGHT - GRAPH_START_Y} pixels")
    print(f"  X-axis: 0 to {X_MAX} (step {X_STEP})")
    print(f"  Y-axis: 0 to {Y_MAX}K (step {Y_STEP}K)")
    print("  Pattern: Build-up → Drop → Recovery")
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

        print("\n[3/4] Creating graph with build-up curve...")
        canvas = create_complete_graph()
        print(f"      ✓ Graph created: {canvas.width}×{canvas.height} pixels")

        print("\n[4/4] Printing to device...")
        printer.set_align("center")
        printer.set_font_size(2, 2)
        printer.println("Build-up Curve Graph")
        printer.feed(8)
        printer.set_font_size(1, 1)
        printer.println("")

        printer.print_bitmap(canvas.width, canvas.height, canvas.data)
        print("      ✓ Bitmap printed")

        printer.feed(2)
        printer.set_font_size(2, 2)
        printer.set_align("center")
        printer.println("PRESSURE")
        printer.feed(3)

        print("\n" + "=" * 60)
        print("✓✓✓ PRINTING COMPLETED! ✓✓✓")
        print("=" * 60)
        print("\nOutput structure:")
        print("  ├─ Title")
        print("  ├─ Y-axis labels at TOP: 0  25K  50K  75K... 200K (rotated 90° CW)")
        print("  ├─ Grid starts BELOW labels")
        print("  ├─ X-axis labels on left: 0, 2, 4... 30 (rotated 90° CW)")
        print("  ├─ Build-up curve (quadratic rise → drop → recovery)")
        print("  ├─ 'TIME' label at bottom (rotated 90° CW)")
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
