"""Read active OBD-II DTCs using python-obd."""

from __future__ import annotations

import argparse
import logging
from typing import Optional

import obd


def parse_args() -> argparse.Namespace:
    """Parse command-line options for connection behavior."""
    parser = argparse.ArgumentParser(description="Read active OBD-II trouble codes")
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port path (for example /dev/tty.usbserial-1410)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Connection timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose python-obd logging",
    )
    return parser.parse_args()


def choose_port(user_port: Optional[str]) -> Optional[str]:
    """Return user-selected port or auto-detected serial device."""
    if user_port:
        return user_port

    scanned_ports = obd.scan_serial()
    if not scanned_ports:
        return None

    return scanned_ports[0]


def main() -> int:
    """Connect to the vehicle ECU and print active trouble codes."""
    args = parse_args()

    obd.logger.setLevel(logging.DEBUG if args.debug else logging.WARNING)

    port_name = choose_port(args.port)
    if port_name:
        print(f"Connecting on {port_name}...")
    else:
        print("No serial port provided or auto-detected. Trying default python-obd scan...")

    connection = obd.OBD(port_name, timeout=args.timeout)
    status = connection.status()

    if status == obd.OBDStatus.CAR_CONNECTED:
        print("Success! Connected to vehicle ECU.")
        print("\nScanning for active trouble codes...")
        response = connection.query(obd.commands.GET_DTC)

        if response and response.value:
            print(f"Found {len(response.value)} Trouble Code(s):")
            for code, description in response.value:
                print(f" - {code}: {description}")
        else:
            print("No check engine light codes found (System Clear).")
        return 0

    if status == obd.OBDStatus.OBD_CONNECTED:
        print("Adapter connected but ECU communication was not established.")
    elif status == obd.OBDStatus.ELM_CONNECTED:
        print("Adapter connected at serial level, but OBD protocol negotiation failed.")
    else:
        print("Could not connect to adapter/vehicle ECU.")

    print("Check ignition state (ON), adapter compatibility, and selected serial port.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())