import serial
import time

# Update with your port. vLinker FS defaults to 115200 baud rate over USB
port = "/dev/tty.usbserial-1410"
baud = 115200 

try:
    # Open the serial port connection
    ser = serial.Serial(port, baud, timeout=1)
    print(f"Connected to serial port {port}")
    
    # 1. Initialize the adapter by sending a reset command
    print("Resetting adapter...")
    ser.write(b"ATZ\r")
    time.sleep(1)
    print(ser.read_all().decode('utf-8', errors='ignore'))
    
    # 2. Tell the adapter to auto-select the car's CAN/OBD protocol
    print("Setting protocol to auto...")
    ser.write(b"ATSP0\r")
    time.sleep(0.5)
    print(ser.read_all().decode('utf-8', errors='ignore'))
    
    # 3. Query Mode 03 (Request Trouble Codes)
    print("Querying vehicle for raw trouble codes (Mode 03)...")
    ser.write(b"03\r")
    time.sleep(1)
    
    # Read response from the car's computer
    raw_response = ser.read_all().decode('utf-8', errors='ignore')
    print("\n--- Raw ECU Response ---")
    print(raw_response)
    print("------------------------")
    
    ser.close()

except Exception as e:
    print(f"Error: {e}")