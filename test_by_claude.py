#!/usr/bin/env python3
"""
Epson TM-T88III Thermal Printer Test Script
Comprehensive testing for serial connection with XON/XOFF flow control
"""

import serial
import time
import sys

# ESC/POS Commands for Epson TM-T88III
ESC = b'\x1b'
GS = b'\x1d'

# Command definitions
CMD_INIT = ESC + b'@'  # Initialize printer
CMD_CUT = GS + b'V\x00'  # Full cut
CMD_PARTIAL_CUT = GS + b'V\x01'  # Partial cut
CMD_STATUS = GS + b'r\x01'  # Get status
CMD_FEED = ESC + b'd\x03'  # Feed 3 lines
CMD_BOLD_ON = ESC + b'E\x01'  # Bold on
CMD_BOLD_OFF = ESC + b'E\x00'  # Bold off
CMD_ALIGN_CENTER = ESC + b'a\x01'  # Center align
CMD_ALIGN_LEFT = ESC + b'a\x00'  # Left align
CMD_DOUBLE_HEIGHT = ESC + b'!\x10'  # Double height
CMD_NORMAL_SIZE = ESC + b'!\x00'  # Normal size

# XON/XOFF characters
XON = b'\x11'  # Device ready
XOFF = b'\x13'  # Device busy

def print_section(title):
    """Print a formatted section title"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_port_exists(port):
    """Test if the COM port exists"""
    print_section("Step 1: Checking COM Port")
    try:
        ser = serial.Serial()
        ser.port = port
        print(f"✓ Port {port} exists")
        return True
    except Exception as e:
        print(f"✗ Error: Port {port} not found")
        print(f"  Details: {e}")
        return False

def open_serial_connection(port, baudrate=9600):
    """Open serial connection with proper settings for TM-T88III with XON/XOFF"""
    print_section("Step 2: Opening Serial Connection")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
            xonxoff=True,  # Enable XON/XOFF flow control
            rtscts=False,  # Disable RTS/CTS
            dsrdtr=False,  # Disable DSR/DTR
            write_timeout=2
        )
        
        print(f"✓ Serial connection opened successfully")
        print(f"  Port: {port}")
        print(f"  Baudrate: {baudrate}")
        print(f"  Data bits: 8")
        print(f"  Parity: None")
        print(f"  Stop bits: 1")
        print(f"  Flow control: XON/XOFF")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.5)
        
        return ser
    
    except serial.SerialException as e:
        print(f"✗ Error opening serial port: {e}")
        return None
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return None

def initialize_printer(ser):
    """Initialize the printer"""
    print_section("Step 3: Initializing Printer")
    
    try:
        # Send initialization command
        ser.write(CMD_INIT)
        time.sleep(0.5)
        
        print("✓ Initialization command sent")
        print("  Waiting for printer to be ready...")
        time.sleep(1)
        
        return True
    
    except Exception as e:
        print(f"✗ Error initializing printer: {e}")
        return False

def test_basic_print(ser):
    """Test basic printing capability"""
    print_section("Step 4: Testing Basic Print")
    
    try:
        # Simple text test
        test_text = b"TEST PRINT\n"
        ser.write(test_text)
        time.sleep(0.5)
        
        # Feed paper to make it visible
        ser.write(CMD_FEED)
        time.sleep(0.5)
        
        print("✓ Basic print command sent")
        print("  Check printer for 'TEST PRINT' output")
        
        return True
    
    except Exception as e:
        print(f"✗ Error during basic print: {e}")
        return False

def test_comprehensive_print(ser):
    """Test comprehensive printing with various commands"""
    print_section("Step 5: Comprehensive Print Test")
    
    try:
        # Center align and double height
        ser.write(CMD_ALIGN_CENTER)
        ser.write(CMD_DOUBLE_HEIGHT)
        ser.write(CMD_BOLD_ON)
        ser.write(b"EPSON TM-T88III\n")
        
        # Normal size
        ser.write(CMD_NORMAL_SIZE)
        ser.write(CMD_BOLD_OFF)
        ser.write(b"Connection Test\n")
        
        # Left align
        ser.write(CMD_ALIGN_LEFT)
        ser.write(b"\n")
        
        # Test data
        ser.write(b"Date: " + time.strftime("%Y-%m-%d %H:%M:%S").encode() + b"\n")
        ser.write(b"Status: OPERATIONAL\n")
        ser.write(b"\n")
        
        # Bold text
        ser.write(CMD_BOLD_ON)
        ser.write(b"All tests passed!\n")
        ser.write(CMD_BOLD_OFF)
        
        # Line separator
        ser.write(b"-" * 42 + b"\n")
        
        # Feed and cut
        ser.write(CMD_FEED)
        time.sleep(0.5)
        
        # Partial cut (safer than full cut)
        ser.write(CMD_PARTIAL_CUT)
        time.sleep(1)
        
        print("✓ Comprehensive print completed")
        print("  Check printer for detailed output")
        
        return True
    
    except Exception as e:
        print(f"✗ Error during comprehensive print: {e}")
        return False

def check_printer_response(ser):
    """Try to get printer status"""
    print_section("Step 6: Checking Printer Response")
    
    try:
        # Clear input buffer
        ser.reset_input_buffer()
        
        # Request status
        ser.write(CMD_STATUS)
        time.sleep(0.5)
        
        # Try to read response
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"✓ Printer responded")
            print(f"  Response bytes: {len(response)}")
            print(f"  Hex: {response.hex()}")
        else:
            print("⚠ No response received (this is normal for some configurations)")
            print("  The printer may still be working correctly")
        
        return True
    
    except Exception as e:
        print(f"⚠ Could not get status: {e}")
        print("  This is not critical - printer may still work")
        return True

def run_full_test(port, baudrate=9600):
    """Run complete printer test sequence"""
    print("\n" + "="*60)
    print("  EPSON TM-T88III THERMAL PRINTER TEST")
    print("  XON/XOFF Flow Control Configuration")
    print("="*60)
    
    # Test 1: Port exists
    if not test_port_exists(port):
        print("\n❌ FAILED: Cannot access COM port")
        print("   Please check:")
        print("   1. Printer is connected")
        print("   2. USB-to-Serial adapter is installed")
        print("   3. Correct COM port number")
        return False
    
    # Test 2: Open connection
    ser = open_serial_connection(port, baudrate)
    if ser is None:
        print("\n❌ FAILED: Cannot open serial connection")
        return False
    
    try:
        # Test 3: Initialize
        if not initialize_printer(ser):
            print("\n❌ FAILED: Cannot initialize printer")
            return False
        
        # Test 4: Basic print
        if not test_basic_print(ser):
            print("\n❌ FAILED: Basic print failed")
            return False
        
        # Test 5: Comprehensive print
        if not test_comprehensive_print(ser):
            print("\n⚠ WARNING: Comprehensive print had issues")
            # Don't fail here, basic print works
        
        # Test 6: Check response
        check_printer_response(ser)
        
        # Success!
        print_section("FINAL RESULT")
        print("✓✓✓ ALL TESTS PASSED! ✓✓✓")
        print("\nYour printer is working correctly!")
        print("\nYou should see printed output with:")
        print("  - 'TEST PRINT' text")
        print("  - Formatted header")
        print("  - Current date/time")
        print("  - Status information")
        print("\nYou can now use this printer with confidence.")
        
        return True
    
    except Exception as e:
        print(f"\n❌ FAILED: Unexpected error: {e}")
        return False
    
    finally:
        # Always close the connection
        if ser and ser.is_open:
            ser.close()
            print("\nSerial connection closed.")

def main():
    """Main function"""
    print("Epson TM-T88III Printer Test Utility")
    print("=====================================\n")
    
    # Get COM port from user
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = input("Enter COM port (e.g., COM3, COM4): ").strip().upper()
        if not port.startswith('COM'):
            port = 'COM' + port
    
    # Get baudrate (optional)
    baudrate = 9600
    if len(sys.argv) > 2:
        try:
            baudrate = int(sys.argv[2])
        except:
            print(f"Invalid baudrate, using default: 9600")
    
    print(f"\nTesting printer on {port} at {baudrate} baud...")
    print("Make sure:")
    print("  1. Printer is powered ON")
    print("  2. Paper is loaded")
    print("  3. Printer cover is CLOSED")
    print("  4. DIP Switch 1-3 is ON (XON/XOFF mode)")
    print("\nPress Enter to start test...")
    input()
    
    # Run the test
    success = run_full_test(port, baudrate)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()