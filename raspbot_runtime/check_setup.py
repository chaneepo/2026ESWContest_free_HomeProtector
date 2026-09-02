"""Check the installed Raspbot software and optionally probe the controller."""

from __future__ import annotations

import argparse
import importlib.metadata
import sys
from pathlib import Path

from smbus2 import SMBus

I2C_BUS = 1
I2C_DEVICE = Path(f"/dev/i2c-{I2C_BUS}")
RASPBOT_ADDRESS = 0x2B
BUTTON_REGISTER = 0x0D


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--probe",
        action="store_true",
        help="read one register from the Raspbot controller at address 0x2B",
    )
    args = parser.parse_args()

    print(f"Python: {sys.executable}")
    try:
        print(f"raspbot package: {importlib.metadata.version('raspbot')}")
    except importlib.metadata.PackageNotFoundError:
        print("ERROR: raspbot package is not installed in this Python environment")
        return 1

    if not I2C_DEVICE.exists():
        print(f"ERROR: {I2C_DEVICE} does not exist")
        return 1
    print(f"I2C device: {I2C_DEVICE} OK")

    if not args.probe:
        print("Software check complete. Add --probe after connecting the chassis board.")
        return 0

    try:
        with SMBus(I2C_BUS) as bus:
            button_value = bus.read_byte_data(RASPBOT_ADDRESS, BUTTON_REGISTER)
    except OSError as exc:
        print(f"ERROR: no response from 0x{RASPBOT_ADDRESS:02X}: {exc}")
        return 2

    print(
        f"Raspbot controller 0x{RASPBOT_ADDRESS:02X}: OK "
        f"(button register={button_value})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
