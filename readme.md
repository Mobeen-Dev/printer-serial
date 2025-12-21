# Epson TM-T88III Thermal Printer - Distribution Graph

A Python script for printing distribution graphs with rotated axis labels on Epson TM-T88III thermal printers. Perfect for visualizing time-series pressure data on receipt paper.

## 📋 Overview

This script generates and prints a professional distribution graph directly to an 80mm thermal printer. All axis labels are rotated 90° clockwise for vertical readability as the paper feeds through the printer.

### What It Prints

![Thermal graph](./media/plot.png)

## 🚀 Quick Start

### Prerequisites

- **Printer**: Epson TM-T88III (80mm)
- **Python**: 3.6 or higher
- **Library**: `pyserial`

### Installation

```bash
# Install required library
pip install pyserial

# Clone or download this script
# Run it
python epson_printer_fixed.py
```

### Configuration

Before running, update the COM port in the script:

```python
# Line ~380 - Update to match your system
printer = EpsonThermalPrinter(port="COM7", baudrate=19200)
```

**Finding Your COM Port:**
- **Windows**: Check Device Manager → Ports (COM & LPT)
- **Linux/Mac**: Usually `/dev/ttyUSB0` or `/dev/ttyS0`

## ⚙️ Customization

### Basic Parameters (Lines 16-29)

```python
# Canvas size
WIDTH = 512          # Printer width in pixels (fixed for 80mm)
HEIGHT = 1200        # Paper length in pixels (adjustable)

# Grid spacing
GRID_X_SPACING = 80  # Pixels between time divisions
GRID_Y_SPACING = 60  # Pixels between pressure divisions
GRID_DASHED = True   # True = dashed lines, False = solid

# Data ranges
X_MAX = 30           # Maximum time value
X_STEP = 2           # Time increment per division
Y_MAX = 200          # Maximum pressure (will show as 200K)
Y_STEP = 25          # Pressure increment per division

# Label spacing
LEFT_MARGIN = 30     # Space for X-axis labels
TOP_MARGIN = 70      # Space for Y-axis labels (CRITICAL!)
BOTTOM_MARGIN = 10   # Space for bottom text
```

### Layout Margins Explained

```
┌─────────────────────────────────┐
│  ← TOP_MARGIN (70px) →          │ Y-axis labels print here
│  Prevents label cutoff!         │
├─────────────────────────────────┤
│L │                              │
│E │     GRAPH AREA               │
│F │     (grid + curve)           │
│T │                              │
│  │                              │
├─────────────────────────────────┤
│  ← BOTTOM_MARGIN (10px) →       │ Bottom text area
└─────────────────────────────────┘
```

### Distribution Curve Parameters (Lines 368-372)

Control the shape of your distribution:

```python
MU = 0.35        # Peak position (0.0 to 1.0, where 0.5 = middle)
SIGMA = 0.15     # Width of distribution (smaller = narrower)
ALPHA = 1.2      # Skew factor (higher = more skewed)
AMPLIFY = 1.5    # Overall amplitude multiplier
```

**Effect Examples:**
- `MU = 0.2` → Peak near top of graph
- `MU = 0.5` → Peak in middle
- `MU = 0.8` → Peak near bottom
- `SIGMA = 0.05` → Very narrow spike
- `SIGMA = 0.3` → Wide, spread-out distribution

## 🎨 Adjusting Label Position

### Y-Axis Labels (Pressure - Horizontal)

**To lower/raise labels** (Line 312, 316):
```python
canvas.draw_text("0", x_pos - 3, 15, 2, rotate_90=True)  # Change y=15
canvas.draw_text(label, x_pos - 3, 15, 2, rotate_90=True)  # Change y=15
```
- **Increase value** → Labels move DOWN
- **Decrease value** → Labels move UP
- **Safe range**: 5 to 50 (within TOP_MARGIN)

### X-Axis Labels (Time - Vertical)

**To adjust horizontal position** (Line 336):
```python
canvas.draw_text(label, 10, y_pos - 3, 2, rotate_90=True)  # Change x=10
```
- **Increase value** → Labels move RIGHT
- **Decrease value** → Labels move LEFT

### Label Size

Change the `size` parameter (last number before `rotate_90`):
```python
canvas.draw_text(label, x, y, 2, rotate_90=True)  # size=2 (current)
canvas.draw_text(label, x, y, 1, rotate_90=True)  # size=1 (smaller)
canvas.draw_text(label, x, y, 3, rotate_90=True)  # size=3 (larger)
```

## 🔧 Printer Settings

### Print Density (Line 389)

```python
printer.set_print_density(10)  # Range: 0-15
```
- **Lower (5-8)**: Lighter print, faster, saves ribbon
- **Higher (10-15)**: Darker print, slower, uses more ribbon
- **Recommended**: 8-10 for best balance

### Print Speed vs Quality

```python
# Adjust on Line 391
printer.set_line_height(24)  # Lower = faster, Higher = better quality
```

## 📊 Common Use Cases

### 1. Different Time Ranges

```python
# For 60-minute timeline (0 to 60, every 5 minutes)
X_MAX = 60
X_STEP = 5
GRID_X_SPACING = 40  # Adjust spacing

# For 24-hour timeline (0 to 24, every 2 hours)
X_MAX = 24
X_STEP = 2
GRID_X_SPACING = 100
```

### 2. Different Pressure Ranges

```python
# For 0-500K range
Y_MAX = 500
Y_STEP = 50  # Every 50K
GRID_Y_SPACING = 50  # Adjust spacing

# For 0-1000K range
Y_MAX = 1000
Y_STEP = 100  # Every 100K
GRID_Y_SPACING = 40
```

### 3. Longer/Shorter Paper

```python
# Short receipt
HEIGHT = 600

# Standard length
HEIGHT = 1200

# Extra long
HEIGHT = 2000
```

## 🐛 Troubleshooting

### Labels Cut Off at Top

**Problem**: Y-axis labels are cut off or overlap with grid

**Solution**: Increase `TOP_MARGIN` (Line 24)
```python
TOP_MARGIN = 90  # Was 70, now 90
```

### Labels Too High/Low

**Problem**: Labels don't align with grid lines

**Solution**: Adjust y-position in draw_text calls (Lines 312, 316)
```python
# Make labels lower
canvas.draw_text(label, x_pos - 3, 20, 2, rotate_90=True)  # Was 5, now 20
```

### Printer Not Responding

1. Check COM port number
2. Verify baudrate (should be 19200)
3. Check USB/serial cable connection
4. Restart printer and try again

### Grid Too Dense/Sparse

**Problem**: Too many or too few grid lines

**Solution**: Adjust spacing parameters
```python
# More divisions (denser grid)
GRID_X_SPACING = 50  # Was 80
GRID_Y_SPACING = 40  # Was 60

# Fewer divisions (sparser grid)
GRID_X_SPACING = 120  # Was 80
GRID_Y_SPACING = 80   # Was 60
```

### Distribution Not Showing

**Problem**: Curve is invisible or outside graph area

**Solution**: Increase AMPLIFY factor (Line 372)
```python
AMPLIFY = 2.5  # Was 1.5, now 2.5
```

## 📝 Code Structure

```
Main Components:
├── EpsonThermalPrinter       # Printer communication class
│   ├── init()                # Connect to printer
│   ├── print_bitmap()        # Send image data
│   └── set_print_density()   # Control darkness
│
├── BitmapCanvas              # Drawing canvas class
│   ├── set_pixel()           # Draw individual pixels
│   ├── draw_char()           # Draw characters
│   ├── draw_text()           # Draw text strings
│   └── draw_*_line()         # Draw lines
│
├── skewed_gaussian()         # Distribution curve function
└── create_complete_graph()   # Main graph generation
```

## 🎯 Key Features

- ✅ **No Label Overlap**: Y-axis labels print FIRST with dedicated space
- ✅ **Rotated Text**: All labels readable when paper feeds through
- ✅ **Customizable**: Easy parameter adjustment for any use case
- ✅ **Professional Output**: Clean grid with smooth distribution curve
- ✅ **Efficient**: Direct bitmap printing for fast output

## 📄 License

Free to use and modify for your projects.

## 🤝 Contributing

Found a bug or want to improve this? Feel free to modify and share your improvements!

---

**Happy Printing! 🖨️**

For questions or issues, check the Troubleshooting section above or review the inline code comments.