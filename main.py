import serial
import time

# Replace with your COM port, e.g. "COM5" on Windows or "/dev/ttyUSB0" on Linux
PORT = "COM11"
BAUD = 9600  # check printer manual, often 9600 or 19200

ser = serial.Serial(PORT, BAUD, timeout=1)

# Initialize printer (ESC @)
ser.write(b'\x1B\x40')

# Print simple text
ser.write(b"Hello from Python!\n")

# Feed 3 lines (ESC d 3)
ser.write(b'\x1B\x64\x03')

# Full cut (GS V 0) - if supported
ser.write(b'\x1D\x56\x00')

ser.flush()
time.sleep(1)
ser.close()
