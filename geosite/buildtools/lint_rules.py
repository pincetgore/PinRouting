#!/usr/bin/env python3
"""
Lint and validation tool for PinRouting Geosite and GeoIP rulesets.

Checks:
- Syntax validity of geosite entries (domain:, full:, keyword:, regexp:).
- Exact duplicate entries within files.
- Redundant subdomains within the same file (e.g., sub.example.com when example.com is present).
- Overly broad or misplaced keyword rules (e.g., keyword:example.com instead of domain:example.com).
- CIDR syntax validity in GeoIP text files.
- Collapsible/redundant CIDR blocks in GeoIP text files.

Usage:
  python3 lint_rules.py [--fail-on-error] [--strict]
"""

import argparse
import ipaddress
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GEOSITE_DIR = REPO_ROOT / "geosite" / "data"
GEOIP_DIR = REPO_ROOT / "geoip"

VALID_GEOSITE_TYPES = {"domain", "full", "keyword", "regexp"}


def lint_geosite_file(filepath: Path, strict: bool = False) -> tuple[int, int]:
    """Lints a single geosite file. Returns (error_count, warning_count)."""
    errors = 0
    warnings = 0
    fn = filepath.name

    seen_exact = {}
    domain_rules = {}  # lower_domain -> line_num
    rules = []  # (line_num, type, value, raw_line)

    with open(filepath, "r", encoding="utf-8") as f:
        for idx, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            # Strip inline comments
            content = line.split("#", 1)[0].strip()
            if not content:
                continue

            # Strip attributes (e.g. @cn)
            parts = content.split("@")[0].strip()
            if ":" in parts:
                rtype, val = parts.split(":", 1)
                rtype = rtype.strip().lower()
                val = val.strip().lower()
            else:
                rtype = "domain"
                val = parts.lower()

            if rtype not in VALID_GEOSITE_TYPES:
                print(f"[ERROR] [{fn}:{idx}] Unknown rule type '{rtype}': {line}")
                errors += 1
                continue

            if not val:
                print(f"[ERROR] [{fn}:{idx}] Empty rule value: {line}")
                errors += 1
                continue

            # Check exact duplicates
            key = f"{rtype}:{val}"
            if key in seen_exact:
                print(f"[ERROR] [{fn}:{idx}] Exact duplicate of line {seen_exact[key]}: '{line}'")
                errors += 1
            else:
                seen_exact[key] = idx

            if rtype == "domain":
                domain_rules[val] = idx
            elif rtype == "keyword":
                # Check if keyword contains domain-like syntax (dot with valid TLD)
                if "." in val and not val.endswith("."):
                    print(f"[WARN] [{fn}:{idx}] 'keyword:{val}' looks like a domain. Use 'domain:{val}' for Trie optimization.")
                    warnings += 1

            rules.append((idx, rtype, val, line))

    # Check for redundant subdomains
    for idx, rtype, val, line in rules:
        if rtype in ("domain", "full"):
            parts = val.split(".")
            for i in range(1, len(parts)):
                parent = ".".join(parts[i:])
                if parent in domain_rules and parent != val:
                    msg = f"[{fn}:{idx}] '{line}' is redundant (covered by 'domain:{parent}' on line {domain_rules[parent]})"
                    if strict:
                        print(f"[ERROR] {msg}")
                        errors += 1
                    else:
                        print(f"[WARN] {msg}")
                        warnings += 1
                    break

    return errors, warnings


def lint_geoip_file(filepath: Path, strict: bool = False) -> tuple[int, int]:
    """Lints a GeoIP CIDR text file. Returns (error_count, warning_count)."""
    errors = 0
    warnings = 0
    fn = filepath.name

    v4_nets = []
    v6_nets = []
    seen = {}

    with open(filepath, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            cidr_str = line.split()[0].split("#")[0].strip()
            try:
                net = ipaddress.ip_network(cidr_str, strict=False)
            except ValueError as e:
                print(f"[ERROR] [{fn}:{idx}] Invalid CIDR '{cidr_str}': {e}")
                errors += 1
                continue

            if cidr_str in seen:
                print(f"[ERROR] [{fn}:{idx}] Duplicate CIDR of line {seen[cidr_str]}: '{cidr_str}'")
                errors += 1
            else:
                seen[cidr_str] = idx

            if net.version == 4:
                v4_nets.append(net)
            else:
                v6_nets.append(net)

    # Check collapsible subnets
    c4 = list(ipaddress.collapse_addresses(v4_nets))
    if len(c4) < len(v4_nets):
        diff = len(v4_nets) - len(c4)
        msg = f"[{fn}] {diff} IPv4 networks can be collapsed into larger/adjacent CIDR blocks."
        if strict:
            print(f"[ERROR] {msg}")
            errors += 1
        else:
            print(f"[WARN] {msg}")
            warnings += 1

    c6 = list(ipaddress.collapse_addresses(v6_nets))
    if len(c6) < len(v6_nets):
        diff = len(v6_nets) - len(c6)
        msg = f"[{fn}] {diff} IPv6 networks can be collapsed into larger/adjacent CIDR blocks."
        if strict:
            print(f"[ERROR] {msg}")
            errors += 1
        else:
            print(f"[WARN] {msg}")
            warnings += 1

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Lint PinRouting Geosite and GeoIP rulesets")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit with non-zero code if errors found")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    total_errors = 0
    total_warnings = 0

    print("=== Linting Geosite Data ===")
    if GEOSITE_DIR.is_dir():
        for item in sorted(GEOSITE_DIR.iterdir()):
            if item.is_file() and not item.name.startswith("."):
                errs, warns = lint_geosite_file(item, strict=args.strict)
                total_errors += errs
                total_warnings += warns
    else:
        print(f"[ERROR] Geosite directory not found: {GEOSITE_DIR}")
        total_errors += 1

    print("\n=== Linting GeoIP Custom Text Lists ===")
    if GEOIP_DIR.is_dir():
        for fn in ["CUSTOM-WHITELIST.txt", "CUSTOM-LIST-ADD.txt", "CUSTOM-FIX-ADD.txt"]:
            item = GEOIP_DIR / fn
            if item.is_file():
                errs, warns = lint_geoip_file(item, strict=args.strict)
                total_errors += errs
                total_warnings += warns

    print("\n=== Lint Summary ===")
    print(f"Total Errors:   {total_errors}")
    print(f"Total Warnings: {total_warnings}")

    if total_errors > 0 and args.fail_on_error:
        sys.exit(1)
    if args.strict and (total_errors > 0 or total_warnings > 0):
        sys.exit(1)


if __name__ == "__main__":
    main()
