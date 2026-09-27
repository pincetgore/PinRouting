"""Automated test runner for PinRouting."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(root_dir: Path) -> int:
    test_script = root_dir / "geosite" / "buildtools" / "test_routing.py"
    if not test_script.exists():
        print(f"Test script not found at {test_script}")
        return 1

    print(f"Running regression test suite: {test_script.name}...")
    res = subprocess.run([sys.executable, str(test_script)], cwd=str(root_dir))
    return res.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PinRouting test suite")
    parser.add_argument("--root-dir", default=str(Path.cwd()), help="PinRouting repo root")
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    return run_tests(root)


if __name__ == "__main__":
    raise SystemExit(main())
