"""Automated test runner for PinRouting: unit tests (tests/) and the routing simulation suite."""

from __future__ import annotations

import argparse
import subprocess
import sys
import unittest
from pathlib import Path


def run_tests(root_dir: Path) -> int:
    print("Running unit tests (tests/)...")
    suite = unittest.defaultTestLoader.discover(str(root_dir / "tests"))
    unit_ok = unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()

    test_script = root_dir / "geosite" / "buildtools" / "test_routing.py"
    print(f"\nRunning regression test suite: {test_script.name}...")
    routing = subprocess.run([sys.executable, str(test_script)], cwd=str(root_dir), check=False)

    return 0 if unit_ok and routing.returncode == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PinRouting test suite")
    parser.add_argument(
        "--root-dir", default=str(Path.cwd()), help="PinRouting repo root"
    )
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    return run_tests(root)


if __name__ == "__main__":
    raise SystemExit(main())
