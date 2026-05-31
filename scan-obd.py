import obd

# Enable debugging if you want to see the raw TX/RX data in the console
obd.logger.setLevel(obd.logging.DEBUG)

# Replace with the exact port you found in Step 2
port_name = "/dev/tty.usbserial-1410" 

print(f"Connecting to vLinker FS on {port_name}...")
connection = obd.OBD(port_name)

# Check if we successfully connected to the adapter and car ECU
if connection.status() == obd.OBDStatus.CAR_CONNECTED:
    print("Success! Connected to vehicle ECU.")
    
    # Mode 03 is the OBD2 command for reading confirmed trouble codes
    print("\nScanning for active trouble codes...")
    dtc_command = obd.commands.GET_DTC
    response = connection.query(dtc_command)
    
    if response.value:
        print(f"Found {len(response.value)} Trouble Code(s):")
        for code, description in response.value:
            print(f" - {code}: {description}")
    else:
        print("No check engine light codes found (System Clear).")
        
else:
    print("Could not connect. Ensure your car ignition is turned to ON.")