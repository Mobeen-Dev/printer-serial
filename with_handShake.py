import serial

ser = serial.Serial(
    port="COM11",
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
    dsrdtr=True    # Enable DTR/DSR handshaking
)
ser.write(b'\n')
ser.write(b'\x1B\x40')         # Initialize
ser.write(b"Hello Printer!\n") # Print text
ser.write(b'\x1B\x64\x02')     # Feed 2 lines
ser.close()
