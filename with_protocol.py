import serial
import time

# Replace COM11 with your port
ser = serial.Serial(
    port="COM7",
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
    xonxoff=True,   # Enable software flow control (XON/XOFF)
    rtscts=False,   # Disable hardware RTS/CTS
    dsrdtr=False    # Disable hardware DSR/DTR
)

# Initialize printer (ESC @)
ser.write(b'\x1B\x40')

# Print text
ser.write(b"Hello Printer with XON/XOFF!\n")

# Feed 3 lines (ESC d 3)
ser.write(b'\x1B\x64\x03')

# Full cut (GS V 0) - may vary per printer
ser.write(b'\x1D\x56\x00')

ser.flush()
time.sleep(0.5)
ser.close()
