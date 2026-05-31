"""Log control module voltage across ignition-off and engine-on phases."""

from __future__ import annotations

import argparse
import csv
import datetime
import logging
import time
from pathlib import Path
from typing import Optional

import obd


def parse_args() -> argparse.Namespace:
    """Parse command-line options for voltage logging."""
    parser = argparse.ArgumentParser(
        description="Log control module voltage to CSV during ignition-off and engine-on phases"
    )
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
        "--interval",
        type=float,
        default=1.0,
        help="Sampling interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--off-duration",
        type=float,
        default=20.0,
        help="Seconds to log with ignition ON and engine OFF (default: 20)",
    )
    parser.add_argument(
        "--on-duration",
        type=float,
        default=30.0,
        help="Seconds to log after engine starts (default: 30)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: output/voltage_log_<timestamp>.csv)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose python-obd logging",
    )
    return parser.parse_args()


def choose_port(user_port: Optional[str]) -> Optional[str]:
    """Return user-selected port or the first auto-detected serial port."""
    if user_port:
        return user_port

    scanned_ports = obd.scan_serial()
    if not scanned_ports:
        return None

    return scanned_ports[0]


def to_voltage_value(response: obd.OBDResponse) -> tuple[Optional[float], str]:
    """Extract numeric voltage from OBD response if available."""
    if response is None:
        return None, "no_response"
    if response.is_null() or response.value is None:
        return None, "null_value"

    try:
        return float(response.value.magnitude), "ok"
    except AttributeError:
        try:
            return float(response.value), "ok"
        except (TypeError, ValueError):
            return None, f"unexpected_value:{response.value}"


def now_iso() -> str:
    """Return current local timestamp in ISO format."""
    return datetime.datetime.now().isoformat(timespec="seconds")


def log_event(
    writer: csv.DictWriter,
    test_start: float,
    phase: str,
    event: str,
    message: str = "",
    voltage_v: Optional[float] = None,
    dtc_code: str = "",
    dtc_description: str = "",
) -> None:
    """Write one normalized log row to CSV."""
    writer.writerow(
        {
            "timestamp": now_iso(),
            "elapsed_s": f"{(time.monotonic() - test_start):.3f}",
            "phase": phase,
            "event": event,
            "voltage_v": "" if voltage_v is None else f"{voltage_v:.3f}",
            "dtc_code": dtc_code,
            "dtc_description": dtc_description,
            "message": message,
        }
    )


def capture_dtc_snapshot(
    connection: obd.OBD,
    writer: csv.DictWriter,
    test_start: float,
    phase: str,
) -> None:
    """Capture and log DTC snapshots for key modes."""
    dtc_queries = [
        ("confirmed_dtc", obd.commands.GET_DTC),
        ("current_cycle_dtc", obd.commands.GET_CURRENT_DTC),
        ("freeze_frame_dtc", obd.commands.FREEZE_DTC),
    ]

    for event_name, command in dtc_queries:
        try:
            response = connection.query(command)
        except Exception as exc:  # defensive logging for diagnosis
            log_event(
                writer,
                test_start,
                phase,
                event_name,
                message=f"query_failed:{exc}",
            )
            continue

        if response and response.value:
            for code, description in response.value:
                log_event(
                    writer,
                    test_start,
                    phase,
                    event_name,
                    message="code_present",
                    dtc_code=code,
                    dtc_description=description,
                )
        else:
            log_event(
                writer,
                test_start,
                phase,
                event_name,
                message="no_codes",
            )


def sample_voltage_for_phase(
    connection: obd.OBD,
    writer: csv.DictWriter,
    test_start: float,
    phase: str,
    duration_s: float,
    interval_s: float,
) -> None:
    """Sample CONTROL_MODULE_VOLTAGE repeatedly for one phase."""
    stop_time = time.monotonic() + duration_s
    while time.monotonic() < stop_time:
        try:
            response = connection.query(obd.commands.CONTROL_MODULE_VOLTAGE)
            voltage_v, message = to_voltage_value(response)
            log_event(
                writer,
                test_start,
                phase,
                "voltage_sample",
                message=message,
                voltage_v=voltage_v,
            )
        except Exception as exc:  # defensive logging for diagnosis
            log_event(
                writer,
                test_start,
                phase,
                "voltage_sample",
                message=f"query_failed:{exc}",
            )

        time.sleep(interval_s)


def main() -> int:
    """Guide a battery voltage test and write readings to CSV."""
    args = parse_args()
    obd.logger.setLevel(logging.DEBUG if args.debug else logging.WARNING)

    port_name = choose_port(args.port)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = Path(
        args.output
        if args.output
        else output_dir / f"voltage_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    print("Battery voltage test: CONTROL_MODULE_VOLTAGE logger")
    print("Step 1: Turn ignition to ON (engine OFF), then press Enter.")
    input()

    print(f"Connecting on {port_name or 'auto'} at {args.baud} baud...")
    connection = obd.OBD(port_name, baudrate=args.baud, timeout=args.timeout)
    status = connection.status()

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "timestamp",
                "elapsed_s",
                "phase",
                "event",
                "voltage_v",
                "dtc_code",
                "dtc_description",
                "message",
            ],
        )
        writer.writeheader()

        test_start = time.monotonic()
        log_event(writer, test_start, "setup", "script_started", message="voltage test initialized")
        log_event(writer, test_start, "setup", "connection_status", message=str(status))

        if status != obd.OBDStatus.CAR_CONNECTED:
            print("Unable to establish ECU connection. Check ignition, adapter, and port.")
            log_event(writer, test_start, "setup", "connection_failed", message=str(status))
            print(f"CSV saved to: {output_path.resolve()}")
            return 1

        print("Connected. Logging with engine OFF...")
        log_event(
            writer,
            test_start,
            "engine_off",
            "phase_start",
            message="ignition_on_engine_off",
        )
        capture_dtc_snapshot(connection, writer, test_start, "engine_off")
        sample_voltage_for_phase(
            connection,
            writer,
            test_start,
            phase="engine_off",
            duration_s=args.off_duration,
            interval_s=args.interval,
        )

        print("Step 2: Start the engine now, then press Enter to continue logging.")
        input()

        print("Logging with engine ON...")
        log_event(
            writer,
            test_start,
            "engine_on",
            "phase_start",
            message="engine_running",
        )
        capture_dtc_snapshot(connection, writer, test_start, "engine_on")
        sample_voltage_for_phase(
            connection,
            writer,
            test_start,
            phase="engine_on",
            duration_s=args.on_duration,
            interval_s=args.interval,
        )

        capture_dtc_snapshot(connection, writer, test_start, "end")
        log_event(writer, test_start, "end", "script_finished", message="test complete")

    print(f"CSV saved to: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
