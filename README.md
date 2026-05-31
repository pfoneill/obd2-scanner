# OBD2 Scanner (Python)

Simple Python-based OBD2 scanner for reading diagnostic trouble codes (DTCs) from a vehicle ECU over a USB OBD adapter (for example, vLinker FS).

This repo currently includes:

- `scan-obd.py`: High-level scan using `python-obd`
- `scan-serial.py`: Low-level raw serial/AT command scan using `pyserial`
- `pixi.toml`: Environment and dependency definition

## Quick Code Review

Current code is a solid first version and should work for basic scanning.

Implemented improvements in this revision:

- Both scripts now support `--port` and auto-detection fallback.

- `scan-obd.py` now supports `--timeout` and has clearer status messaging when adapter/ECU connection fails.

- `scan-serial.py` now catches `serial.SerialException` explicitly for better troubleshooting.

- Debug logging in `scan-obd.py` is now optional via `--debug`.

- Open follow-up item: validate whether the current Python pin in `pixi.toml` should be lowered for broader package compatibility.

## Prerequisites

- macOS
- USB OBD2 adapter (ELM327-compatible or similar)
- Vehicle ignition set to `ON` (engine can be off for many reads)
- [Pixi](https://pixi.sh/) installed

## Setup

From the repo root:

```bash
pixi install
```

Then enter the environment:

```bash
pixi shell
```

## Find Your Adapter Serial Port (macOS)

Plug in the adapter and run:

```bash
ls /dev/tty.*
```

Look for a device like:

- `/dev/tty.usbserial-1410`
- `/dev/tty.usbmodem...`

Both scripts now support auto-detection. If auto-detection picks the wrong device, pass an explicit port with `--port`.

## Usage

### 1) High-level OBD scan (`python-obd`)

```bash
python scan-obd.py
```

Optional flags:

```bash
python scan-obd.py --port /dev/tty.usbserial-1410 --debug --timeout 30
```

Expected behavior:

- Connects to the adapter and ECU
- Queries Mode 03 (confirmed DTCs)
- Prints codes and descriptions if present

### 2) Raw serial scan (`pyserial`)

```bash
python scan-serial.py
```

Optional flags:

```bash
python scan-serial.py --port /dev/tty.usbserial-1410 --baud 115200 --timeout 1.0
```

Expected behavior:

- Sends `ATZ` (adapter reset)
- Sends `ATSP0` (auto protocol)
- Sends `03` (DTC request)
- Prints raw ECU response

## Interpreting Results

- If `scan-obd.py` prints codes like `P0xxx`, those are active confirmed trouble codes.
- If no codes are returned, ECU may report system clear.
- Raw response in `scan-serial.py` can help diagnose adapter/protocol issues.

## Troubleshooting

- Connection failed:
  - Confirm ignition is `ON`
  - Re-check serial port path
  - Unplug/replug adapter and retry
- Permission issues opening serial port:
  - Close other apps that may have claimed the port
- No ECU response:
  - Ensure adapter supports your vehicle protocol
  - Try another OBD app to validate adapter health
- Garbled serial output:
  - Confirm baud is `115200` for your adapter

## Roadmap (Suggested Next Steps)

- Add CLI arguments (`--port`, `--debug`, `--timeout`)
- Add auto port detection and selection prompt
- Add structured output (`--json`) for logs/automation
- Add unit tests for response parsing and error handling
- Add optional support for freeze frame and pending codes

## Disclaimer

This project is for diagnostic assistance only. Follow safe operating practices and never interact with tools while driving.
