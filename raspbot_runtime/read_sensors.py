"""Read Raspbot line tracking and optional ultrasonic distance sensors."""

from __future__ import annotations

import argparse
import time

from raspbot import RaspbotError

from chan_control import RaspbotController


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--with-ultrasonic", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.count <= 100:
        parser.error("--count must be between 1 and 100")
    if not 0.1 <= args.interval <= 10.0:
        parser.error("--interval must be between 0.1 and 10 seconds")

    try:
        with RaspbotController() as controller:
            for index in range(1, args.count + 1):
                line = controller.read_line()
                message = f"[{index}/{args.count}] line={line} raw=0x{line.raw:02X}"
                if args.with_ultrasonic:
                    message += f" distance={controller.read_distance_cm():.1f}cm"
                print(message)
                if index < args.count:
                    time.sleep(args.interval)
    except (OSError, RaspbotError) as exc:
        print(f"Hardware error: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
