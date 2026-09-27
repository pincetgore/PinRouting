"""PinRouting unified command line interface."""

from __future__ import annotations

import argparse
import sys

from pinrouting.cli import build, lint, test


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pinrouting",
        description="Unified PinRouting CLI for building, linting, and testing routing configs.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Build subcommand
    build_parser = subparsers.add_parser("build", help="Build all client routing configs")
    build_parser.add_argument("--repo", default="pincetgore/PinRouting", help="GitHub owner/repo")
    build_parser.add_argument("--epoch", default=None, help="Epoch timestamp")
    build_parser.add_argument("--root-dir", default=".", help="Root repo directory")

    # Lint subcommand
    lint_parser = subparsers.add_parser("lint", help="Lint profile manifests and geosite definitions")
    lint_parser.add_argument("--root-dir", default=".", help="Root repo directory")

    # Test subcommand
    test_parser = subparsers.add_parser("test", help="Run routing regression tests")
    test_parser.add_argument("--root-dir", default=".", help="Root repo directory")

    args = parser.parse_args()

    if args.subcommand == "build":
        return build.main(sys.argv[2:])
    elif args.subcommand == "lint":
        return lint.main(sys.argv[2:])
    elif args.subcommand == "test":
        return test.main(sys.argv[2:])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
