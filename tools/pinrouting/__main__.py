"""PinRouting unified command line interface."""

from __future__ import annotations

import argparse
import sys

from pinrouting.cli import build, check_dead, lint, test


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pinrouting",
        description="Unified PinRouting CLI for building, linting, testing, and verifying routing configs.",
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

    # Check-dead subcommand
    check_parser = subparsers.add_parser("check-dead", help="Check and clean up dead domains and IP CIDRs")
    check_parser.add_argument("--root-dir", default=".", help="Root repo directory")
    check_parser.add_argument(
        "--target",
        choices=["all", "domains", "ips"],
        default="all",
        help="Target resources to verify (default: all)",
    )
    check_parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove dead entries from files in-place",
    )
    check_parser.add_argument(
        "--resolvers",
        default="1.1.1.1,8.8.8.8,77.88.8.8",
        help="Comma-separated DNS resolvers (default: 1.1.1.1,8.8.8.8,77.88.8.8)",
    )
    check_parser.add_argument("--dns-timeout", type=float, default=2.0, help="DNS query timeout in seconds")
    check_parser.add_argument("--ip-timeout", type=float, default=1.5, help="TCP/ping check timeout in seconds")
    check_parser.add_argument("--concurrency", type=int, default=150, help="Concurrent check tasks")
    check_parser.add_argument(
        "--max-sample-hosts",
        type=int,
        default=5,
        help="Max sample hosts for CIDR subnets",
    )
    check_parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry attempts for transient network failures",
    )
    check_parser.add_argument(
        "--exclude-files",
        default="",
        help="Comma-separated list of filenames to exclude from checking",
    )
    check_parser.add_argument(
        "--output-markdown",
        default="",
        help="Path to write Markdown summary report",
    )
    check_parser.add_argument(
        "--output-json",
        default="",
        help="Path to write JSON details report",
    )

    args = parser.parse_args()

    if args.subcommand == "build":
        return build.main(sys.argv[2:])
    elif args.subcommand == "lint":
        return lint.main(sys.argv[2:])
    elif args.subcommand == "test":
        return test.main(sys.argv[2:])
    elif args.subcommand == "check-dead":
        return check_dead.main(sys.argv[2:])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
