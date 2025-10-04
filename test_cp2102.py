import serial
import time

def db9_loopback_test(port="COM11", baudrate=9600, test_message=b"LOOP\n"):
    """
    Perform a DB9 loopback test.
    
    - Short TX (Pin 3) ↔ RX (Pin 2) on DB9 connector.
    - Verifies the PC → MAX232 → DB9 ↔ loopback wiring.
    
    Parameters:
        port (str): The COM port to open (e.g., "COM11").
        baudrate (int): The baud rate for communication.
        test_message (bytes): The test message to send.
    """
    ser = None
    try:
        # Open serial port
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.5,
            dsrdtr=False
        )
        
        # Clear any stale data in buffer
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Send test string
        print(f"Sending: {test_message.decode().strip()}")
        ser.write(test_message)

        # Small delay before reading response
        time.sleep(0.1)

        # Read echoed data
        response = ser.read(len(test_message))

        if response:
            print("RX:", response.decode(errors="replace").strip())
            if response == test_message:
                print("✅ Loopback successful: Adapter + MAX232 wiring are fine.")
            else:
                print("⚠️ Data received but does not match test message.")
        else:
            print("❌ No data received. Check adapter/MAX232 wiring and pin mapping.")

    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    finally:
        # if 'ser' in locals() and ser.is_open:
        ser.close() # type: ignore


if __name__ == "__main__":
    db9_loopback_test(port="COM11", baudrate=9600)
