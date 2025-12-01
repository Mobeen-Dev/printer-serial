#!/usr/bin/env python3
"""
Epson TM-T88III (80mm) - Rotated Left-Skewed Distribution with Grid
X-axis: Runs DOWN the paper length (vertical)
Y-axis: Runs ACROSS the paper width (horizontal, 512 dots)
"""

import serial
import time
import math

# === ESC/POS Commands ===
ESC = b'\x1b'
GS = b'\x1d'

# === Adjustable parameters ===
WIDTH = 512    # 80mm printer width (72mm printable = 512 dots)
HEIGHT = 800   # Paper length (taller = longer receipt)
GRID_X_SPACING = 80   # Spacing along paper length (X-axis)
GRID_Y_SPACING = 64   # Spacing across paper width (Y-axis)
GRID_DASHED = True    # Dashed grid lines
# ==============================

class EpsonThermalPrinter:
    def __init__(self, port='COM7', baudrate=9600):
        """Initialize the printer connection"""
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3,
            xonxoff=True,  # XON/XOFF flow control
            rtscts=False,
            dsrdtr=False,
            write_timeout=3
        )
        
        # Clear buffers
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.5)
        
        # Initialize printer
        self.begin()
        self.set_default()
    
    def begin(self):
        """Initialize printer"""
        self.ser.write(ESC + b'@')  # Initialize
        time.sleep(0.5)
    
    def set_default(self):
        """Set printer to default settings"""
        self.ser.write(ESC + b'@')
        time.sleep(0.3)
    
    def set_print_density(self, density=8, breakTime=2):
        """
        Set print density and heating parameters
        density: 0-15 (higher = darker)
        breakTime: 0-7 (heating interval)
        """
        printSetting = (density << 4) | breakTime
        # DC2 # n - Set printing density
        self.ser.write(bytes([0x12, 0x23, printSetting]))
        time.sleep(0.1)
    
    def set_line_height(self, val=32):
        """Set line spacing"""
        if val < 24:
            val = 24
        self.ser.write(ESC + b'3' + bytes([val]))
        time.sleep(0.1)
    
    def println(self, text=""):
        """Print text with newline"""
        self.ser.write(text.encode('ascii', errors='replace') + b'\n')
        time.sleep(0.1)
    
    def print_bitmap(self, width, height, bitmap_data):
        """
        Print bitmap using GS v 0 command
        
        GS v 0 m xL xH yL yH [data...]
        - m = 0 (normal), 1 (double width), 2 (double height), 3 (quad)
        - xL, xH = width in bytes (little endian)
        - yL, yH = height in dots (little endian)
        """
        width_bytes = width // 8
        
        # Prepare command header
        cmd = GS + b'v0'  # GS v 0
        cmd += bytes([0])  # m = 0 (normal size)
        cmd += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])  # xL, xH
        cmd += bytes([height & 0xFF, (height >> 8) & 0xFF])  # yL, yH
        
        # Send command header
        self.ser.write(cmd)
        time.sleep(0.05)
        
        # Send bitmap data in chunks
        chunk_size = 1024
        for i in range(0, len(bitmap_data), chunk_size):
            chunk = bitmap_data[i:i + chunk_size]
            self.ser.write(chunk)
            time.sleep(0.02)
        
        time.sleep(0.5)
    
    def feed(self, lines=1):
        """Feed paper by specified lines"""
        self.ser.write(ESC + b'd' + bytes([lines]))
        time.sleep(lines * 0.1)
    
    def close(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()


class BitmapCanvas:
    def __init__(self, width, height):
        """
        Initialize bitmap canvas
        Width: across the paper (512 dots for 80mm printer)
        Height: down the paper length
        """
        self.width = width
        self.height = height
        self.bytes_per_line = width // 8
        self.data = bytearray(self.bytes_per_line * height)
    
    def clear(self):
        """Clear bitmap to all white"""
        self.data = bytearray(self.bytes_per_line * self.height)
    
    def set_pixel(self, x, y):
        """
        Set a pixel to black
        x: horizontal position (0 to width-1, across paper)
        y: vertical position (0 to height-1, down paper)
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        
        byte_index = (x // 8) + y * self.bytes_per_line
        bit_position = x & 7
        self.data[byte_index] |= (0x80 >> bit_position)
    
    def draw_vertical_line(self, x, dashed=False):
        """Draw vertical line (goes DOWN the paper)"""
        for y in range(self.height):
            if not dashed or (y // 4) % 2 == 0:
                self.set_pixel(x, y)
    
    def draw_horizontal_line(self, y, dashed=False):
        """Draw horizontal line (goes ACROSS the paper)"""
        for x in range(self.width):
            if not dashed or (x // 4) % 2 == 0:
                self.set_pixel(x, y)
    
    def draw_grid(self, y_spacing, x_spacing, dashed=True):
        """
        Draw grid pattern
        y_spacing: spacing down the paper (X-axis of graph)
        x_spacing: spacing across the paper (Y-axis of graph)
        """
        # Horizontal grid lines (across paper, constant Y)
        for y in range(0, self.height, y_spacing):
            self.draw_horizontal_line(y, dashed)
        
        # Vertical grid lines (down paper, constant X)
        for x in range(0, self.width, x_spacing):
            self.draw_vertical_line(x, dashed)
    
    def draw_thick_point(self, x, y, thickness=2):
        """Draw a thick point"""
        for dy in range(-1, 2):  # -1, 0, 1
            for dx in range(-thickness, thickness + 1):
                self.set_pixel(x + dx, y + dy)


def skewed_gaussian(x, mu, sigma, alpha):
    """Left-skewed Gaussian distribution"""
    z = (x - mu) / sigma
    base = math.exp(-0.5 * z * z)
    skew = 1.0 - alpha * (x - mu)
    if skew < 0:
        skew = 0
    return base * skew


def draw_rotated_distribution(canvas):
    """
    Draw distribution rotated 90 degrees
    X-axis: Goes DOWN the paper (HEIGHT dimension)
    Y-axis: Goes ACROSS the paper (WIDTH dimension)
    The curve runs from top to bottom of the receipt
    """
    values = []
    max_val = 0.0
    
    # --- Shape tuning ---
    MU = 0.35        # Peak position (0.35 = upper part of paper)
    SIGMA = 0.15     # Width of distribution
    ALPHA = 1.2      # Skew amount
    AMPLIFY = 1.5    # Height amplification
    # --------------------
    
    # Calculate distribution values along the HEIGHT (paper length)
    for y in range(HEIGHT):
        # Normalize y to 0-1 range (this is our "x" in the distribution)
        yf = y / (HEIGHT - 1)
        v = skewed_gaussian(yf, MU, SIGMA, ALPHA)
        v *= AMPLIFY
        values.append(v)
        if v > max_val:
            max_val = v
    
    if max_val < 1e-6:
        max_val = 1.0
    
    # Draw the curve
    # For each Y position (going down the paper)
    # Calculate the X position (going across the paper)
    for y in range(HEIGHT):
        n = values[y] / max_val
        # Center the curve and extend across the width
        center_x = WIDTH // 2
        extent = int(n * (WIDTH // 2 - 20))  # Leave margin
        
        # Draw from center outward (both directions for symmetric curve)
        x = center_x + extent
        canvas.draw_thick_point(x, y, 2)
    
    # Draw center line (baseline of rotated graph)
    for y in range(0, HEIGHT, 2):
        canvas.set_pixel(WIDTH // 2, y)


def draw_vertical_axis_labels(canvas):
    """Draw simple axis markers"""
    # Left edge marker line
    for y in range(0, HEIGHT, 10):
        canvas.set_pixel(5, y)
    
    # Right edge marker line  
    for y in range(0, HEIGHT, 10):
        canvas.set_pixel(WIDTH - 5, y)


def main():
    """Main function"""
    print("Epson TM-T88III (80mm) - Rotated Distribution Graph")
    print("=" * 60)
    print("Configuration:")
    print(f"  Printer Width: {WIDTH} dots (80mm paper)")
    print(f"  Graph Height: {HEIGHT} dots (paper length)")
    print(f"  Orientation: X-axis DOWN, Y-axis ACROSS")
    print(f"  Grid: {GRID_X_SPACING}×{GRID_Y_SPACING} pixels")
    print("=" * 60)
    
    # Connect to printer
    print("\n[1/6] Connecting to printer on COM7...")
    try:
        printer = EpsonThermalPrinter(port='COM7', baudrate=9600)
        print("      ✓ Connected")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return
    
    try:
        # Configure printer
        print("\n[2/6] Configuring printer...")
        printer.set_print_density(10)  # Slightly darker for better visibility
        printer.set_line_height(24)
        print("      ✓ Configuration applied")
        
        # Create bitmap canvas
        print("\n[3/6] Creating bitmap canvas...")
        canvas = BitmapCanvas(WIDTH, HEIGHT)
        canvas.clear()
        print(f"      ✓ Canvas: {WIDTH}×{HEIGHT} ({len(canvas.data)} bytes)")
        
        # Draw grid
        print("\n[4/6] Drawing grid...")
        canvas.draw_grid(GRID_X_SPACING, GRID_Y_SPACING, GRID_DASHED)
        print("      ✓ Grid pattern drawn")
        
        # Draw axis labels
        print("\n[5/6] Drawing distribution...")
        draw_vertical_axis_labels(canvas)
        draw_rotated_distribution(canvas)
        print("      ✓ Distribution curve drawn")
        
        # Print to device
        print("\n[6/6] Printing to device...")
        printer.println("80mm Rotated Left-Skewed Distribution")
        printer.println("X-axis: DOWN | Y-axis: ACROSS")
        printer.println("")
        print("      → Sending bitmap data...")
        
        printer.print_bitmap(WIDTH, HEIGHT, canvas.data)
        print("      ✓ Bitmap printed")
        
        printer.feed(3)
        print("      ✓ Complete")
        
        print("\n" + "=" * 60)
        print("✓✓✓ PRINTING COMPLETED! ✓✓✓")
        print("=" * 60)
        print("\nExpected output:")
        print("  ├─ Full 80mm width coverage")
        print("  ├─ Grid pattern with dashed lines")
        print("  ├─ Distribution curve running DOWN the paper")
        print("  ├─ Y-axis extending ACROSS the paper width")
        print("  └─ Center baseline visible")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        printer.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()