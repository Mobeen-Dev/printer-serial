#!/usr/bin/env python3
"""
Epson TM-T88III - Tall Left-Skewed Distribution with Grid
48 mm (384 dots) wide, variable height for long paper
"""

import serial
import time
import math
import struct

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

class EpsonBitmapPrinter:
    def __init__(self, port='COM7', baudrate=9600):
        """Initialize the printer connection"""
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
            xonxoff=True,  # XON/XOFF flow control
            rtscts=False,
            dsrdtr=False,
            write_timeout=2
        )
        
        # Clear buffers
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.5)
        
        # Initialize printer
        self.initialize()
    
    def initialize(self):
        """Initialize printer to default state"""
        self.ser.write(ESC + b'@')  # Initialize
        time.sleep(0.5)
    
    def set_print_density(self, density=8):
        """Set print density (0-15)"""
        # GS ( K <Function 50>
        # For TM-T88III, density control may vary
        # Using heating time and heating dots control
        heatTime = 80 + density * 10
        heatInterval = 2
        
        # ESC 7 n1 n2 n3
        self.ser.write(ESC + bytes([55, min(heatTime, 255), heatInterval, 0]))
        time.sleep(0.1)
    
    def set_line_height(self, dots=24):
        """Set line height in dots"""
        self.ser.write(ESC + b'3' + bytes([dots]))
        time.sleep(0.1)
    
    def print_text(self, text):
        """Print text string"""
        self.ser.write(text.encode('ascii') + b'\n')
        time.sleep(0.1)
    
    def print_bitmap(self, width, height, bitmap_data):
        """
        Print bitmap using ESC * command (bit image mode)
        For large images, split into chunks
        """
        bytes_per_line = width // 8
        
        # Print line by line
        for y in range(height):
            # ESC * m nL nH [data]
            # m = 33 (24-dot double-density)
            # For TM-T88III: use mode 0, 1, 32, or 33
            
            # Extract one line of data
            line_start = y * bytes_per_line
            line_end = line_start + bytes_per_line
            line_data = bitmap_data[line_start:line_end]
            
            # Send bitmap line command
            # ESC * m nL nH
            nL = width & 0xFF
            nH = (width >> 8) & 0xFF
            
            self.ser.write(ESC + b'*' + bytes([0, nL, nH]) + line_data)
            self.ser.write(b'\n')  # Advance to next line
            
            # Small delay every few lines to prevent buffer overflow
            if y % 10 == 0:
                time.sleep(0.01)
        
        time.sleep(0.5)
    
    def feed(self, lines=1):
        """Feed paper by specified lines"""
        self.ser.write(ESC + b'd' + bytes([lines]))
        time.sleep(0.3)
    
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
        self.data = bytearray(self.bytes_per_line * height)
    
    def clear(self):
        """Clear bitmap to all white"""
        self.data = bytearray(self.bytes_per_line * self.height)
    
    def set_pixel(self, x, y):
        """Set a pixel to black"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        
        byte_index = (x // 8) + y * self.bytes_per_line
        bit_position = 7 - (x % 8)  # MSB first
        self.data[byte_index] |= (1 << bit_position)
    
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
        """Draw a thick point"""
        for dy in range(-thickness, thickness + 1):
            for dx in range(-1, 2):  # -1, 0, 1
                self.set_pixel(x + dx, y + dy)


def skewed_gaussian(x, mu, sigma, alpha):
    """
    Left-skewed Gaussian distribution
    x: input value (0-1)
    mu: mean
    sigma: standard deviation
    alpha: skew factor (negative for left skew)
    """
    z = (x - mu) / sigma
    base = math.exp(-0.5 * z * z)
    skew = 1.0 - alpha * (x - mu)  # negative α = left skew
    if skew < 0:
        skew = 0
    return base * skew


def draw_left_skewed_distribution(canvas):
    """Draw left-skewed tall distribution"""
    values = []
    max_val = 0.0
    
    # --- Shape tuning ---
    MU = 0.65
    SIGMA = 0.20
    ALPHA = 1.2
    AMPLIFY = 1.5
    # ---------------------
    
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
    """Main function"""
    print("Epson TM-T88III - Bitmap Distribution Printer")
    print("=" * 50)
    
    # Initialize printer
    print("\n1. Connecting to printer on COM7...")
    try:
        printer = EpsonBitmapPrinter(port='COM7', baudrate=9600)
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Error connecting to printer: {e}")
        return
    
    try:
        # Configure printer
        print("\n2. Configuring printer...")
        printer.set_print_density(8)
        printer.set_line_height(24)
        print("✓ Printer configured")
        
        # Create bitmap
        print("\n3. Creating bitmap canvas...")
        canvas = BitmapCanvas(WIDTH, HEIGHT)
        canvas.clear()
        print("✓ Canvas created")
        
        # Draw grid
        print("\n4. Drawing grid...")
        canvas.draw_grid(GRID_X_SPACING, GRID_Y_SPACING, GRID_DASHED)
        print("✓ Grid drawn")
        
        # Draw distribution
        print("\n5. Drawing left-skewed distribution...")
        draw_left_skewed_distribution(canvas)
        print("✓ Distribution drawn")
        
        # Print header text
        print("\n6. Printing to device...")
        printer.print_text("Tall Left-Skewed Distribution with Grid")
        time.sleep(0.5)
        
        # Print bitmap
        print("   Printing bitmap (this may take a minute)...")
        printer.print_bitmap(WIDTH, HEIGHT, canvas.data)
        print("✓ Bitmap printed")
        
        # Feed paper
        printer.feed(4)
        
        print("\n" + "=" * 50)
        print("✓✓✓ PRINTING COMPLETED SUCCESSFULLY! ✓✓✓")
        print("=" * 50)
        print("\nCheck your printer output!")
        
    except Exception as e:
        print(f"\n✗ Error during printing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always close connection
        printer.close()
        print("\nPrinter connection closed.")


if __name__ == "__main__":
    main()