"""Read active OBD-II DTCs and supported commands using python-obd."""

from __future__ import annotations

import argparse
import datetime
import logging
from pathlib import Path
from typing import Optional

import obd

# Diagnostic modes to query for trouble codes.
# GET_DTC         = Mode 03 confirmed codes
# GET_CURRENT_DTC = Mode 04 current codes
# FREEZE_DTC      = Mode 02 freeze frame snapshot code
_DTC_COMMANDS = [
    ("Confirmed DTCs (Mode 03)",      obd.commands.GET_DTC),
    ("Current DTCs (Mode 04)",        obd.commands.GET_CURRENT_DTC),
    ("Freeze Frame DTC (Mode 02)",    obd.commands.FREEZE_DTC),
]


def parse_args() -> argparse.Namespace:
    """Parse command-line options for connection behavior."""
    parser = argparse.ArgumentParser(description="Read OBD-II diagnostics and supported commands")
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port path (for example /dev/tty.usbserial-D3BA5IT8)",
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
        default=30.0,
        help="Connection timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: vehicle_diagnostics_<timestamp>.txt)",
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


def query_dtcs(connection: obd.OBD, out: list[str]) -> None:
    """Query all DTC modes and append results to out."""
    for label, cmd in _DTC_COMMANDS:
        out.append(f"\n{'='*60}")
        out.append(f"{label}")
        out.append(f"{'='*60}")
        try:
            response = connection.query(cmd)
            if response and response.value:
                out.append(f"  {len(response.value)} code(s) found:")
                for code, description in response.value:
                    out.append(f"  [{code}]  {description}")
            else:
                out.append("  No codes found.")
        except Exception as exc:
            out.append(f"  Query failed: {exc}")


def query_supported_commands(connection: obd.OBD, out: list[str]) -> None:
    """List all commands the ECU reported as supported."""
    out.append(f"\n{'='*60}")
    out.append("Supported ECU Commands")
    out.append(f"{'='*60}")
    supported = connection.supported_commands
    if not supported:
        out.append("  No supported commands returned.")
        return

    for cmd in sorted(supported, key=lambda c: (c.mode or 0, c.pid if c.pid is not None else 0)):
        mode_str = f"{cmd.mode:02X}" if cmd.mode is not None else "--"
        pid_str  = str(cmd.pid) if cmd.pid is not None else ""
        out.append(f"  [{mode_str}/{pid_str:>4}]  {cmd.name:<40}  {cmd.desc}")


def main() -> int:
    """Connect to the vehicle ECU, scan diagnostics, and write results to file."""
    args = parse_args()

    obd.logger.setLevel(logging.DEBUG if args.debug else logging.WARNING)

    port_name = choose_port(args.port)
    if port_name:
        print(f"Connecting on {port_name} at {args.baud} baud...")
    else:
        print("No serial port provided or auto-detected. Trying default python-obd scan...")

    connection = obd.OBD(port_name, baudrate=args.baud, timeout=args.timeout)
    status = connection.status()

    if status != obd.OBDStatus.CAR_CONNECTED:
        if status == obd.OBDStatus.OBD_CONNECTED:
            print("Adapter connected but ECU communication was not established.")
        elif status == obd.OBDStatus.ELM_CONNECTED:
            print("Adapter connected at serial level, but OBD protocol negotiation failed.")
        else:
            print("Could not connect to adapter/vehicle ECU.")
        print("Check ignition state (ON), adapter compatibility, and selected serial port.")
        return 1

    print("Success! Connected to vehicle ECU.")

    # Collect all output into a list of lines for both console and file.
    lines: list[str] = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"OBD-II Vehicle Diagnostic Report")
    lines.append(f"Generated  : {timestamp}")
    lines.append(f"Port       : {port_name}")
    lines.append(f"Baud       : {args.baud}")

    query_dtcs(connection, lines)
    query_supported_commands(connection, lines)

    report = "\n".join(lines)
    print(report)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = Path(
        args.output
        if args.output
        else output_dir / f"vehicle_diagnostics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    output_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {output_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())