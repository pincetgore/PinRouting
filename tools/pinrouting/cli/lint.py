"""Linter for PinRouting profiles and rule files.

Verifies:
- All profiles conform to official Happ / INCY schema requirements
- All referenced geosite: categories exist in geosite/data/
- All referenced geoip: categories exist in geoip/ or are standard (cn, ru, by, private, direct, whitelist)
- DNS addresses and hosts are valid
- No duplicate domains in geosite lists
- No syntax errors in CIDRs
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import subprocess
import sys
from pathlib import Path

from pinrouting.models import ProfileConfig


class ValidationError(Exception):
    pass


def lint_profiles(root_dir: Path) -> list[str]:
    errors: list[str] = []
    profiles_dir = root_dir / "profiles"
    geosite_data_dir = root_dir / "geosite" / "data"

    available_geosites = {
        p.name
        for p in geosite_data_dir.iterdir()
        if p.is_file() and not p.name.startswith(".")
    }
    standard_geoips = {
        "private",
        "ru",
        "by",
        "cn",
        "direct",
        "whitelist",
        "custom-list-add",
        "custom-whitelist",
        "ads",
    }

    profile_files = sorted(profiles_dir.glob("*.json"))
    if not profile_files:
        errors.append(f"No profiles found in {profiles_dir}")
        return errors

    for pf in profile_files:
        try:
            with open(pf, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cfg = ProfileConfig.from_dict(raw)
        except (json.JSONDecodeError, OSError, ValueError, KeyError) as e:
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
                if cat not in standard_geoips:
                    errors.append(f"[{pf.name}] Unknown geoip category '{cat}'")
            else:
                # Must be a valid CIDR
                try:
                    ipaddress.ip_network(ip_rule, strict=False)
                except ValueError:
                    errors.append(f"[{pf.name}] Invalid CIDR rule '{ip_rule}'")

    return errors


def lint_geosites(root_dir: Path) -> list[str]:
    errors: list[str] = []
    geosite_data_dir = root_dir / "geosite" / "data"

    for p in sorted(geosite_data_dir.glob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        seen_domains: dict[str, int] = {}
        with open(p, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # check for simple formatting issues
                if " " in line:
                    errors.append(
                        f"[{p.name}:{idx}] Line contains unescaped space: '{line}'"
                    )
                domain = line.split(":", 1)[1].strip() if ":" in line else line
                if domain in seen_domains:
                    errors.append(
                        f"[{p.name}:{idx}] Duplicate domain rule: '{domain}' (first defined at line {seen_domains[domain]})"
                    )
                seen_domains[domain] = idx

    return errors


def run_rules_linter(root_dir: Path) -> int:
    rules_linter = root_dir / "geosite" / "buildtools" / "lint_rules.py"
    if not rules_linter.is_file():
        return 0
    res = subprocess.run(
        [sys.executable, str(rules_linter), "--fail-on-error"],
        cwd=str(root_dir),
        check=False,
    )
    return res.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint PinRouting declarative profiles and data files"
    )
    parser.add_argument(
        "--root-dir", default=str(Path.cwd()), help="PinRouting repo root"
    )
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    print("Linting PinRouting profiles and rulesets...")
    profile_errors = lint_profiles(root)
    geosite_errors = lint_geosites(root)

    all_errors = profile_errors + geosite_errors
    if all_errors:
        print(f"\n❌ Found {len(all_errors)} error(s):")
        for err in all_errors:
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
