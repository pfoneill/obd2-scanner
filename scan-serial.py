"""Send raw ELM327 commands over serial to request DTCs."""

from __future__ import annotations

import argparse
import time
from typing import Optional

import serial
from serial.tools import list_ports


def parse_args() -> argparse.Namespace:
    """Parse command-line options for serial scanning."""
    parser = argparse.ArgumentParser(description="Query raw OBD-II trouble codes over serial")
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port path (for example /dev/tty.usbserial-1410)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Serial baud rate (default: 115200)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Serial read timeout in seconds (default: 1.0)",
    )
    return parser.parse_args()


def auto_detect_port() -> Optional[str]:
    """Pick the most likely USB serial device on the host."""
    ports = list(list_ports.comports())
    if not ports:
        return None

    preferred_markers = (
        "usbserial",
        "usbmodem",
        "wchusbserial",
        "cp210",
        "ftdi",
    )

    def score(port_info: list_ports.ListPortInfo) -> int:
        details = f"{port_info.device} {port_info.description} {port_info.hwid}".lower()
        return 0 if any(marker in details for marker in preferred_markers) else 1

    ranked_ports = sorted(ports, key=score)
    return ranked_ports[0].device


def send_and_read(ser: serial.Serial, command: str, wait_seconds: float) -> str:
    """Send one AT/OBD command and return decoded response text."""
    ser.write(f"{command}\r".encode("ascii"))
    time.sleep(wait_seconds)
    return ser.read_all().decode("utf-8", errors="ignore")


def main() -> int:
    """Open serial port, initialize adapter, and request mode 03."""
    args = parse_args()
    port = args.port or auto_detect_port()

    if not port:
        print("No serial port found. Connect adapter or pass --port.")
        return 1

    try:
        with serial.Serial(port, args.baud, timeout=args.timeout) as ser:
            print(f"Connected to serial port {port}")

            print("Resetting adapter...")
            print(send_and_read(ser, "ATZ", 1.0))

            print("Setting protocol to auto...")
            print(send_and_read(ser, "ATSP0", 0.5))

            print("Querying vehicle for raw trouble codes (Mode 03)...")
            raw_response = send_and_read(ser, "03", 1.0)

            print("\n--- Raw ECU Response ---")
            print(raw_response)
            print("------------------------")

        return 0
    except serial.SerialException as exc:
        print(f"Serial error: {exc}")
        print("Check adapter connection, port path, and whether another app is using the port.")
        return 1
    except OSError as exc:
        print(f"OS error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())