#!/usr/bin/env python3
"""
Epson TM-T88III - Tall Left-Skewed Distribution with Grid
48 mm (384 dots) wide, variable height for long paper
Compatible with Adafruit_Thermal.printBitmap() format
"""

import serial
import time
import math

# === ESC/POS Commands ===
ESC = b'\x1b'
GS = b'\x1d'

# === Adjustable parameters ===
WIDTH = 384   # printer width (48mm)
HEIGHT = 320  # plot height — taller = longer paper
GRID_X_SPACING = 32   # vertical grid spacing (pixels)
GRID_Y_SPACING = 40   # horizontal grid spacing (pixels)
GRID_DASHED = True    # dashed grid lines
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
    
    def print_bitmap(self, width, height, bitmap_data, lsb_first=False):
        """
        Print bitmap using GS v 0 command (matches Adafruit_Thermal)
        
        GS v 0 m xL xH yL yH [data...]
        - m = 0 (normal), 1 (double width), 2 (double height), 3 (quad)
        - xL, xH = width in bytes (little endian)
        - yL, yH = height in dots (little endian)
        """
        width_bytes = width // 8
        
        # Prepare command header
        # GS v 0 m xL xH yL yH
        cmd = GS + b'v0'  # GS v 0
        cmd += bytes([0])  # m = 0 (normal size)
        cmd += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])  # xL, xH
        cmd += bytes([height & 0xFF, (height >> 8) & 0xFF])  # yL, yH
        
        # Send command header
        self.ser.write(cmd)
        time.sleep(0.05)
        
        # Send bitmap data in chunks to prevent buffer overflow
        chunk_size = 1024
        for i in range(0, len(bitmap_data), chunk_size):
            chunk = bitmap_data[i:i + chunk_size]
            self.ser.write(chunk)
            time.sleep(0.02)  # Small delay between chunks
        
        # Wait for printing to complete
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
        """Initialize bitmap canvas"""
        self.width = width
        self.height = height
        self.bytes_per_line = width // 8
        # Initialize bitmap data (row-major order, MSB first)
        self.data = bytearray(self.bytes_per_line * height)
    
    def clear(self):
        """Clear bitmap to all white (0x00)"""
        self.data = bytearray(self.bytes_per_line * self.height)
    
    def set_pixel(self, x, y):
        """
        Set a pixel to black (matches Adafruit library)
        Format: MSB first, left to right
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        
        # Calculate byte index (row-major order)
        byte_index = (x // 8) + y * self.bytes_per_line
        
        # Set bit (MSB first: 0x80 >> bit_position)
        bit_position = x & 7  # x % 8
        self.data[byte_index] |= (0x80 >> bit_position)
    
    def draw_vertical_line(self, x, dashed=False):
        """Draw vertical line"""
        for y in range(self.height):
            if not dashed or (y // 4) % 2 == 0:
                self.set_pixel(x, y)
    
    def draw_horizontal_line(self, y, dashed=False):
        """Draw horizontal line"""
        for x in range(self.width):
            if not dashed or (x // 4) % 2 == 0:
                self.set_pixel(x, y)
    
    def draw_grid(self, x_spacing, y_spacing, dashed=True):
        """Draw grid pattern"""
        # Vertical grid lines
        for x in range(0, self.width, x_spacing):
            self.draw_vertical_line(x, dashed)
        
        # Horizontal grid lines
        for y in range(0, self.height, y_spacing):
            self.draw_horizontal_line(y, dashed)
    
    def draw_thick_point(self, x, y, thickness=2):
        """Draw a thick point (matches C code)"""
        for dy in range(-thickness, thickness + 1):
            for dx in range(-1, 2):  # -1, 0, 1
                self.set_pixel(x + dx, y + dy)


def skewed_gaussian(x, mu, sigma, alpha):
    """
    Left-skewed Gaussian distribution (matches C code exactly)
    """
    z = (x - mu) / sigma
    base = math.exp(-0.5 * z * z)
    skew = 1.0 - alpha * (x - mu)  # negative α = left skew
    if skew < 0:
        skew = 0
    return base * skew


def draw_left_skewed_tall(canvas):
    """Draw left-skewed tall distribution (matches C code)"""
    values = []
    max_val = 0.0
    
    # --- Shape tuning (exact match to C code) ---
    MU = 0.65
    SIGMA = 0.20
    ALPHA = 1.2
    AMPLIFY = 1.5
    # --------------------------------------------
    
    # Calculate distribution values
    for x in range(WIDTH):
        xf = x / (WIDTH - 1)
        v = skewed_gaussian(xf, MU, SIGMA, ALPHA)
        v *= AMPLIFY
        values.append(v)
        if v > max_val:
            max_val = v
    
    if max_val < 1e-6:
        max_val = 1.0
    
    # Draw the curve
    for x in range(WIDTH):
        n = values[x] / max_val
        y = HEIGHT - 1 - int(n * (HEIGHT - 10))
        canvas.draw_thick_point(x, y, 2)
    
    # Draw baseline
    for x in range(0, WIDTH, 2):
        canvas.set_pixel(x, HEIGHT - 1)


def main():
    """Main function (matches C setup())"""
    print("Epson TM-T88III - Bitmap Distribution Printer")
    print("=" * 60)
    print("Configuration:")
    print(f"  Width: {WIDTH} dots ({WIDTH/8} mm)")
    print(f"  Height: {HEIGHT} dots")
    print(f"  Grid: {GRID_X_SPACING}x{GRID_Y_SPACING} pixels")
    print(f"  Dashed: {GRID_DASHED}")
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
        # Configure printer (matches C code)
        print("\n[2/6] Configuring printer...")
        printer.set_print_density(8)
        printer.set_line_height(24)
        print("      ✓ Density: 8, Line height: 24")
        
        # Create and clear bitmap
        print("\n[3/6] Creating bitmap canvas...")
        canvas = BitmapCanvas(WIDTH, HEIGHT)
        canvas.clear()
        print(f"      ✓ Canvas: {WIDTH}x{HEIGHT} ({len(canvas.data)} bytes)")
        
        # Draw grid
        print("\n[4/6] Drawing grid...")
        canvas.draw_grid(GRID_X_SPACING, GRID_Y_SPACING, GRID_DASHED)
        print(f"      ✓ Grid drawn")
        
        # Draw distribution
        print("\n[5/6] Drawing left-skewed distribution...")
        draw_left_skewed_tall(canvas)
        print("      ✓ Distribution curve drawn")
        
        # Print to device
        print("\n[6/6] Printing to device...")
        printer.println("Tall Left-Skewed Distribution with Grid")
        print("      → Header printed")
        
        print("      → Sending bitmap data...")
        printer.print_bitmap(WIDTH, HEIGHT, canvas.data)
        print("      ✓ Bitmap printed")
        
        printer.feed(4)
        print("      ✓ Paper fed")
        
        print("\n" + "=" * 60)
        print("✓✓✓ PRINTING COMPLETED SUCCESSFULLY! ✓✓✓")
        print("=" * 60)
        print("\nExpected output:")
        print("  - Header text at top")
        print("  - Dashed grid pattern")
        print("  - Left-skewed bell curve")
        print("  - Baseline at bottom")
        
    except Exception as e:
        print(f"\n✗ Error during printing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        printer.close()
        print("\nSerial connection closed.")


if __name__ == "__main__":
    main()