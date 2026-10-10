"""PinRouting unified command line interface."""

from __future__ import annotations

import argparse

from pinrouting.cli import build, check_dead, lint, test

SUBCOMMANDS = {
    "build": build.main,
    "lint": lint.main,
    "test": test.main,
    "check-dead": check_dead.main,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pinrouting",
        description="Unified PinRouting CLI for building, linting, testing, and verifying routing configs.",
        epilog="Run 'pinrouting <subcommand> --help' for subcommand options.",
    )
    parser.add_argument("subcommand", choices=SUBCOMMANDS)
    parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    ns = parser.parse_args()
    return SUBCOMMANDS[ns.subcommand](ns.args)


if __name__ == "__main__":
    raise SystemExit(main())
