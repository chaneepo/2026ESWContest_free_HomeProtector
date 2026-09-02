"""Run a deliberately short and speed-limited Raspbot movement test."""

from __future__ import annotations

import argparse

from raspbot import RaspbotError

from chan_control import Motion, RaspbotController


def main() -> int:
    actions = [motion.value for motion in Motion] + ["stop"]
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=actions)
    parser.add_argument("--speed", type=int, default=40)
    parser.add_argument("--duration", type=float, default=0.2)
    parser.add_argument(
        "--confirm-wheels-off-ground",
        action="store_true",
        help="required for every movement other than stop",
    )
    args = parser.parse_args()

    if args.action != "stop" and not args.confirm_wheels_off_ground:
        parser.error(
            "movement refused: raise all four wheels and add "
            "--confirm-wheels-off-ground"
        )

    controller = RaspbotController()
    try:
        controller.connect()
        if args.action == "stop":
            controller.stop()
            print("All motors stopped.")
        else:
            controller.pulse(
                Motion(args.action), speed=args.speed, duration=args.duration
            )
            print(
                f"Completed {args.action}: speed={args.speed}, "
                f"duration={args.duration:.2f}s"
            )
    except (OSError, RaspbotError) as exc:
        print(f"Hardware error: {exc}")
        return 2
    finally:
        controller.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
