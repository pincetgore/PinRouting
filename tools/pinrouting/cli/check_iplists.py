"""Sanity gates for the daily geoip build: a broken upstream list must stop the release, not reroute users."""

from __future__ import annotations

import argparse
import ipaddress
from pathlib import Path

# IPv4 addresses a built list may cover. In 11.2026 direct covered 49.0M and whitelist 0.22M: one
# 0.0.0.0/0 line in an upstream "add" list would otherwise send nearly all traffic DIRECT, past the VPN.
MAX_IPV4_ADDRESSES = {"direct": 80_000_000, "whitelist": 1_000_000}
# Foreign addresses (Google DNS) that must never be routed DIRECT
MUST_NOT_CONTAIN = ("8.8.8.8", "2001:4860:4860::8888")


def check_built_list(name: str, text: str) -> list[str]:
    """Checks one text dump of the geoip builder (output/text/<name>.txt). Returns error messages."""
    cidrs = (line.split("#", 1)[0].strip() for line in text.splitlines())
    nets = [ipaddress.ip_network(c, strict=False) for c in cidrs if c]
    errors: list[str] = []
    total = sum(n.num_addresses for n in ipaddress.collapse_addresses(n for n in nets if n.version == 4))
    if total > MAX_IPV4_ADDRESSES[name]:
        errors.append(f"{name}.txt covers {total:,} IPv4 addresses, limit is {MAX_IPV4_ADDRESSES[name]:,}")
    for ip in MUST_NOT_CONTAIN:
        addr = ipaddress.ip_address(ip)
        hit = next((n for n in nets if addr in n), None)
        if hit:
            errors.append(f"{name}.txt would route {ip} DIRECT (via {hit})")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pinrouting check-iplists", description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    output = sub.add_parser("output", help="check the built direct.txt / whitelist.txt")
    output.add_argument("text_dir", type=Path, help="geoip builder output/text dir")
    args = parser.parse_args(argv)

    errors: list[str] = []
    for name in MAX_IPV4_ADDRESSES:
        errors += check_built_list(name, (args.text_dir / f"{name}.txt").read_text(encoding="utf-8"))
    for err in errors:
        print(f"::error::{err}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
