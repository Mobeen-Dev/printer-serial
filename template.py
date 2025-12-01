import serial
import time

# Adjust this to your USB-to-serial adapter COM port
# On Windows: "COM3" or "COM4"
# On Linux/Mac: "/dev/ttyUSB0"
SERIAL_PORT = "COM11"
BAUDRATE = 9600  # Must match DIP switch setting
TIMEOUT = 1

# ESC/POS commands
ESC = b'\x1b'
GS = b'\x1d'

INIT_PRINTER = ESC + b'@'          # Reset
CUT_FULL = GS + b'V' + b'\x00'     # Full cut
CUT_PARTIAL = GS + b'V' + b'\x01'  # Partial cut

try:
    printer = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT,
        xonxoff=True,   # set True if DIP switches set to XON/XOFF
        rtscts=False,    # set True if DIP switches set to RTS/CTS
        dsrdtr=False     # set True if DIP switches set to DTR/DSR
    )

    if printer.is_open:
        print("Printer connection opened successfully")

        # Reset printer
        printer.write(INIT_PRINTER)
        time.sleep(0.5)

        # Send text
        printer.write(b"Hello World!\n")
        printer.write(b"Testing ESC/POS direct...\n\n")

        # Cut paper
        printer.write(CUT_FULL)

        print("Data sent to printer")

    printer.close()

except Exception as e:
    print(f"Error: {e}")
