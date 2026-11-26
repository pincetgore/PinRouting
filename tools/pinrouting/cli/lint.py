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
import json
import subprocess
import sys
from pathlib import Path

from pinrouting.models import ProfileConfig, ProfileError


def geosite_categories(root_dir: Path) -> set[str]:
    """Category names in geosite/data (one file each)."""
    return {p.name for p in (root_dir / "geosite" / "data").iterdir() if p.is_file() and not p.name.startswith(".")}


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


def category_problems(cfg: ProfileConfig, geosites: set[str], geoips: set[str]) -> list[str]:
    """The model checked the values; what is left needs the repo: do the referenced categories exist?"""
    problems = [
        f"Unknown geosite category '{site.split(':', 1)[1]}' (referenced as '{site}')"
        for site in cfg.direct_sites + cfg.proxy_sites + cfg.block_sites
        if site.split(":", 1)[1] not in geosites
    ]
    unbuilt = [
        cat for rule in cfg.direct_ip + cfg.proxy_ip + cfg.block_ip
        if (cat := rule.removeprefix("geoip:")) != rule and cat not in geoips
    ]
    return problems + [
        f"geoip category '{cat}' is not built by geoip/config.json (available: {', '.join(sorted(geoips))})"
        for cat in unbuilt
    ]


def lint_profiles(root_dir: Path) -> list[str]:
    errors: list[str] = []
    profiles_dir = root_dir / "profiles"
    available_geosites = geosite_categories(root_dir)
    available_geoips = built_geoip_categories(root_dir)

    profile_files = sorted(profiles_dir.glob("*.json"))
    if not profile_files:
        errors.append(f"No profiles found in {profiles_dir}")
        return errors

    for pf in profile_files:
        try:
            cfg = ProfileConfig.load_from_file(pf)
        except ProfileError as e:
            problems = e.problems
        except (json.JSONDecodeError, OSError, TypeError) as e:
            problems = [f"Failed to parse profile: {e}"]
        else:
            problems = category_problems(cfg, available_geosites, available_geoips)
        errors += [f"[{pf.name}] {p}" for p in problems]

    return errors


def run_rules_linter(root_dir: Path) -> int:
    rules_linter = root_dir / "geosite" / "buildtools" / "lint_rules.py"
    sys.stdout.flush()  # or the child's output lands before ours in CI logs
    res = subprocess.run(
        [sys.executable, str(rules_linter)],
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
