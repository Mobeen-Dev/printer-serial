import serial.tools.list_ports


def list_available_serial_ports():
    """
    Retrieves and displays all currently available serial (COM) ports.

    This function utilizes the 'pyserial' library to query the system's
    hardware registry for active serial interfaces. It prints the device
    name (e.g., COM3 or /dev/ttyUSB0) alongside its hardware description.

    Returns:
        list: A list of ListPortInfo objects for further programmatic use.
    """
    # Fetch the list of available ports from the system
    ports = serial.tools.list_ports.comports()

    if not ports:
        print("--- No serial ports detected ---")
        return []

    print(f"{'Device':<20} | {'Description'}")
    print("-" * 50)

    for port in ports:
        # .device: The device path or name
        # .description: The user-friendly name provided by the OS/driver
        print(f"{port.device:<20} | {port.description}")

    return ports


if __name__ == "__main__":
    # The entry point of the script
    print("Scanning for hardware interfaces...\n")
    list_available_serial_ports()
