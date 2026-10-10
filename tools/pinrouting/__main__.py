"""PinRouting unified command line interface."""

from __future__ import annotations

import argparse
import importlib

# Subcommand -> module in pinrouting.cli. Imported lazily so build/lint/test don't need
# check-dead's network dependencies (dnspython) installed.
SUBCOMMANDS = {
    "build": "build",
    "lint": "lint",
    "test": "test",
    "check-dead": "check_dead",
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
    module = importlib.import_module(f"pinrouting.cli.{SUBCOMMANDS[ns.subcommand]}")
    return module.main(ns.args)


if __name__ == "__main__":
    raise SystemExit(main())
