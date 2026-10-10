"""Linter for PinRouting profiles and rule files.

Verifies:
- All profiles conform to official Happ / INCY schema requirements
- All referenced geosite: categories exist in geosite/data/
- All referenced geoip: categories are actually produced by geoip/config.json (+ private)
- DNS addresses and hosts are valid
- Geosite / GeoIP rule syntax via geosite/buildtools/lint_rules.py
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import subprocess
import sys
from pathlib import Path

from pinrouting.models import ProfileConfig


def built_geoip_categories(root_dir: Path) -> set[str]:
    """Category names the geoip builder will put into geoip.dat."""
    with open(root_dir / "geoip" / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    names: set[str] = set()
    for entry in config["input"]:
        if entry.get("action") != "add":
            continue
        args = entry.get("args", {})
        if entry["type"] == "private":
            names.add("private")
        elif "name" in args:
            names.add(args["name"])
        else:
            names.update(args.get("wantedList", {}))
    return {n.lower() for n in names}


def lint_profiles(root_dir: Path) -> list[str]:
    errors: list[str] = []
    profiles_dir = root_dir / "profiles"
    geosite_data_dir = root_dir / "geosite" / "data"

    available_geosites = {
        p.name
        for p in geosite_data_dir.iterdir()
        if p.is_file() and not p.name.startswith(".")
    }
    available_geoips = built_geoip_categories(root_dir)

    profile_files = sorted(profiles_dir.glob("*.json"))
    if not profile_files:
        errors.append(f"No profiles found in {profiles_dir}")
        return errors

    for pf in profile_files:
        try:
            cfg = ProfileConfig.load_from_file(pf)
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as e:
            errors.append(f"[{pf.name}] Failed to parse profile: {e}")
            continue

        # Check required fields
        if not cfg.name:
            errors.append(f"[{pf.name}] Profile Name cannot be empty")
        if cfg.global_proxy not in ("true", "false"):
            errors.append(
                f"[{pf.name}] GlobalProxy must be 'true' or 'false', got '{cfg.global_proxy}'"
            )
        if cfg.remote_dns_type not in ("DoH", "DoH3", "DoU", "DoT"):
            errors.append(
                f"[{pf.name}] RemoteDNSType '{cfg.remote_dns_type}' is not supported"
            )
        if cfg.domestic_dns_type not in ("DoH", "DoH3", "DoU", "DoT"):
            errors.append(
                f"[{pf.name}] DomesticDNSType '{cfg.domestic_dns_type}' is not supported"
            )

        # Validate DnsHosts
        for domain, ip in cfg.dns_hosts.items():
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                errors.append(
                    f"[{pf.name}] Invalid IP '{ip}' for host '{domain}' in DnsHosts"
                )

        # Check geosite references
        all_sites = cfg.direct_sites + cfg.proxy_sites + cfg.block_sites
        for site in all_sites:
            if site.startswith("geosite:"):
                cat = site.split(":", 1)[1]
                if cat not in available_geosites:
                    errors.append(
                        f"[{pf.name}] Unknown geosite category '{cat}' (referenced as '{site}')"
                    )

        # Check geoip references
        all_ips = cfg.direct_ip + cfg.proxy_ip + cfg.block_ip
        for ip_rule in all_ips:
            if ip_rule.startswith("geoip:"):
                cat = ip_rule.split(":", 1)[1]
                if cat not in available_geoips:
                    errors.append(
                        f"[{pf.name}] geoip category '{cat}' is not built by geoip/config.json "
                        f"(available: {', '.join(sorted(available_geoips))})"
                    )
            else:
                # Must be a valid CIDR
                try:
                    ipaddress.ip_network(ip_rule, strict=False)
                except ValueError:
                    errors.append(f"[{pf.name}] Invalid CIDR rule '{ip_rule}'")

    return errors


def run_rules_linter(root_dir: Path) -> int:
    rules_linter = root_dir / "geosite" / "buildtools" / "lint_rules.py"
    res = subprocess.run(
        [sys.executable, str(rules_linter), "--fail-on-error"],
        cwd=str(root_dir),
        check=False,
    )
    return res.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pinrouting lint",
        description="Lint PinRouting declarative profiles and data files",
    )
    parser.add_argument(
        "--root-dir", default=str(Path.cwd()), help="PinRouting repo root"
    )
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    print("Linting PinRouting profiles...")
    profile_errors = lint_profiles(root)
    if profile_errors:
        print(f"\n❌ Found {len(profile_errors)} error(s):")
        for err in profile_errors:
            print(f"  - {err}")
        return 1

    # Run geosite/geoip syntax & redundancy linter
    rules_code = run_rules_linter(root)
    if rules_code != 0:
        return rules_code

    print("✓ All profiles and rule definitions are valid!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
