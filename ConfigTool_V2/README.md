# BMIoT ConfigTool v2.0

A desktop GUI application for generating **Modbus_Config.json** and **ParamMap_Config.json** configuration files for the Thermelgy BMIoT ESP32 gateway firmware.

## Overview

The BMIoT ConfigTool provides a 9-step wizard that guides field engineers through the complete configuration of a BMIoT gateway — from defining Modbus devices and registers to generating the final JSON files the firmware requires.

**What it produces:**

| Output File | Purpose |
|---|---|
| `Modbus_Config.json` | Defines RS-485 communication: slave addresses, packets, registers, write pairs |
| `ParamMap_Config.json` | Maps registers to Lua LBI slots, cloud telemetry groups, NVS setpoints, and MQTT network settings |

## Features

- **9-step guided wizard** — each step feeds the next, enforcing correct order
- **Automatic computation** — packet grouping, parameter IDs, LBI slot assignment, cloud group structure are all auto-calculated
- **Live validation** — errors and warnings displayed before generation
- **Project save/load** — save work-in-progress as `.bmiot_project` files
- **Import from JSON** — import existing Modbus_Config.json and ParamMap_Config.json files
- **Single EXE** — no installation required, runs standalone on Windows

## Wizard Steps

| Step | Page | Purpose |
|------|------|---------|
| 1 | Project Setup | Project name, baud rate, serial data format |
| 2 | Devices & Slaves | Add Modbus devices and their slave addresses |
| 3 | Registers | Define registers: address, FC, FMT, multiplier |
| 4 | Link B (Feedback) | Pair write registers with hardware feedback reads |
| 5 | LBI Slots | Assign Lua script access slots to registers |
| 6 | Cloud Groups | Configure MQTT telemetry cluster groups |
| 7 | NVS Setpoints | Define cloud-writable persistent values |
| 8 | Network / MQTT | Set broker IP, port, device IDs |
| 9 | Generate JSON | Validate and produce output files |

## Requirements

- **Python 3.10+**
- **PySide6 >= 6.5.0**

## Running from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Building the EXE

```bash
pip install pyinstaller
pyinstaller BMIoT_ConfigTool_v2.spec
```

The output EXE will be in `dist/BMIoT_ConfigTool_v2.exe`.

## Project Structure

```
Source/
├── main.py                     Entry point
├── requirements.txt            Python dependencies
├── BMIoT_ConfigTool_v2.spec    PyInstaller build spec
├── Import_Examples/            Example JSON files for testing import
└── bmiot_configtool_v2/        Python package
    ├── engine/                 Generation engine, models, validator, importer
    ├── ui/                     PySide6 GUI (main window, styles, project I/O)
    │   └── pages/              One page per wizard step
    └── tests/                  Unit tests
```

## Documentation

See the `Docs/` folder for detailed guides:

| Document | Description |
|---|---|
| `USER_GUIDE.md` | End-user guide — walks through every step with examples |
| `BMIoT_ConfigTool_Development_Plan.md` | Engineering specification and algorithms |
| `BMIoT_ConfigTool_Visual_Guide.md` | Visual step-by-step flow diagrams |
| `BMIoT_Config_Logic_Guide.md` | Firmware configuration logic reference |

## Release

The pre-built Windows EXE is available in `Release/BMIoT_ConfigTool_v2.exe`.

No installation required — download and run.

## License

Proprietary — Thermelgy Products.
