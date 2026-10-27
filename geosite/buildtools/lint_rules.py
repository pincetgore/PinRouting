#!/usr/bin/env python3
"""
Lint and validation tool for PinRouting Geosite and GeoIP rulesets.

Checks:
- Syntax validity of geosite entries (domain:, full:, keyword:, regexp:).
- Exact duplicate entries within files.
- Redundant subdomains within the same file (e.g., sub.example.com when example.com is present).
- Overly broad or misplaced keyword rules (e.g., keyword:example.com instead of domain:example.com).
- CIDR syntax validity in GeoIP text files.
- Collapsible/redundant CIDR blocks in GeoIP text files with detailed suggestions.

Usage:
  python3 lint_rules.py [--fail-on-error] [--strict]
"""

import argparse
import ipaddress
import re
import sys
from bisect import bisect_right
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from pinrouting.geosite import is_valid_domain, is_valid_keyword, split_rule

GEOSITE_DIR = REPO_ROOT / "geosite" / "data"
GEOIP_DIR = REPO_ROOT / "geoip"

VALID_GEOSITE_TYPES = {"domain", "full", "keyword", "regexp"}
ATTR_RE = re.compile(r"@[a-z0-9!]+")


def lint_geosite_file(filepath: Path, strict: bool = False) -> tuple[int, int]:
    """Lints a single geosite file with the same rules v2fly applies when building geosite.dat.

    Returns (error_count, warning_count).
    """
    errors = 0
    warnings = 0
    fn = filepath.name

    seen_exact = {}
    domain_rules = {}  # lower_domain -> line_num
    rules = []  # (line_num, type, value, raw_line)

    def error(idx: int, msg: str) -> None:
        nonlocal errors
        print(f"[ERROR] [{fn}:{idx}] {msg}")
        errors += 1

    with open(filepath, "r", encoding="utf-8") as f:
        for idx, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            parsed = split_rule(line)
            if parsed is None:
                continue
            rtype, fields = parsed

            if rtype not in VALID_GEOSITE_TYPES:
                error(idx, f"Unknown rule type '{rtype}': {line}")
                continue
            if not fields:
                error(idx, f"Empty rule value: {line}")
                continue
            # Only @attr is supported: &affiliation and include: are ignored by Shadowrocket and the tests
            bad = [x for x in fields[1:] if not ATTR_RE.fullmatch(x)]
            if bad:
                error(idx, f"Unsupported field(s) {bad} (only @attr allowed): {line}")
                continue

            val = fields[0] if rtype == "regexp" else fields[0].lower()
            if rtype in ("domain", "full") and not is_valid_domain(val):
                error(idx, f"Invalid domain '{val}' (v2fly allows a-z, 0-9, '-', '.'; IDN must be punycode): {line}")
                continue
            if rtype == "keyword" and not is_valid_keyword(val):
                error(idx, f"Invalid keyword '{val}': {line}")
                continue
            if rtype == "regexp":
                try:
                    re.compile(val)
                except re.error as e:
                    error(idx, f"Invalid regexp: {e}: {line}")
                    continue

            # Check exact duplicates
            key = f"{rtype}:{val}"
            if key in seen_exact:
                error(idx, f"Exact duplicate of line {seen_exact[key]}: '{line}'")
            else:
                seen_exact[key] = idx

            if rtype == "domain":
                domain_rules[val] = idx
            elif rtype == "keyword" and "." in val and not val.endswith("."):
                # Check if keyword contains domain-like syntax (dot with valid TLD)
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


def _format_collapse_details[TNetwork: (ipaddress.IPv4Network, ipaddress.IPv6Network)](
    nets: list[TNetwork],
    collapsed: list[TNetwork],
    line_map: dict[str, int],
) -> str:
    """Helper to format detailed information about collapsed subnets."""
    # Only networks that vanished on collapse need explaining; find each one's cover by binary search
    # (scanning every pair is O(n^2) and took ~2 minutes on the 18k-line whitelist)
    starts = [int(n.network_address) for n in collapsed]  # collapse_addresses returns sorted networks
    covered: dict[TNetwork, list[TNetwork]] = {}
    for s in set(nets) - set(collapsed):
        cover = collapsed[bisect_right(starts, int(s.network_address)) - 1]
        covered.setdefault(cover, []).append(s)
    details = []
    for net, subs in sorted(covered.items()):
        subs_str = ", ".join(f"{s} (line {line_map.get(str(s), '?')})" for s in sorted(subs))
        details.append(f"'{net}' can cover: {subs_str}")
    return "; ".join(details)


def lint_geoip_file(filepath: Path, strict: bool = False) -> tuple[int, int]:
    """Lints a GeoIP CIDR text file. Returns (error_count, warning_count)."""
    errors = 0
    warnings = 0
    fn = filepath.name

    v4_nets: list[ipaddress.IPv4Network] = []
    v6_nets: list[ipaddress.IPv6Network] = []
    seen = {}
    line_map = {}

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
                line_map[str(net)] = idx

            if isinstance(net, ipaddress.IPv4Network):
                v4_nets.append(net)
            else:
                v6_nets.append(net)

    # Check collapsible subnets
    c4 = list(ipaddress.collapse_addresses(v4_nets))
    if len(c4) < len(v4_nets):
        diff = len(v4_nets) - len(c4)
        details = _format_collapse_details(v4_nets, c4, line_map)
        msg = f"[{fn}] {diff} IPv4 network(s) can be collapsed: {details}"
        if strict:
            print(f"[ERROR] {msg}")
            errors += 1
        else:
            print(f"[WARN] {msg}")
            warnings += 1

    c6 = list(ipaddress.collapse_addresses(v6_nets))
    if len(c6) < len(v6_nets):
        diff = len(v6_nets) - len(c6)
        details = _format_collapse_details(v6_nets, c6, line_map)
        msg = f"[{fn}] {diff} IPv6 network(s) can be collapsed: {details}"
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
        for item in sorted(GEOIP_DIR.glob("*.txt")):
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
