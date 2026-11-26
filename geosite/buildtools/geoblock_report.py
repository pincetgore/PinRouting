#!/usr/bin/env python3
"""Reports domains from third-party geoblock lists that the Happ profiles route DIRECT.

A service that refuses Russian IPs breaks when it goes DIRECT, e.g. a google.com host caught by
domain:google.com in geosite:whitelist. The report changes nothing: add real misses to
geosite/data/category-geoblock-ru, deliberate ones to geoblock_allow_direct.txt.

Usage:
  python3 geoblock_report.py LIST [LIST ...]   # one domain per line or hosts lines, "#" comments
Exit code 1 when something is routed DIRECT.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from pathlib import Path

BUILDTOOLS = Path(__file__).resolve().parent
sys.path[:0] = [str(BUILDTOOLS), str(BUILDTOOLS.parent.parent / "tools")]

from pinrouting.geosite import is_valid_domain
from test_routing import REPO_ROOT, GeositeMatcher, RoutingTestSuite

ALLOW_DIRECT = BUILDTOOLS / "geoblock_allow_direct.txt"


def parse_domains(text: str) -> set[str]:
    """Domains of a plain or hosts-format list; tokens that are not valid domains are skipped."""
    lasts = (line.split("#", 1)[0].split()[-1:] for line in text.splitlines())
    names = (t[0].lower().strip(".") for t in lasts if t)
    return {n for n in names if is_valid_domain(n)}


def find_direct(
    domains: Iterable[str], resolvers: dict[str, Callable[[str], str]], allowed: Callable[[str], bool]
) -> dict[str, list[str]]:
    """Profile -> sorted domains it routes DIRECT, minus the allowed ones."""
    candidates = [d for d in domains if not allowed(d)]
    return {name: sorted(d for d in candidates if resolve(d) == "DIRECT") for name, resolve in resolvers.items()}


def main(argv: list[str] | None = None) -> int:
    paths = [Path(p) for p in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        print(__doc__)
        return 2
    domains = set().union(*(parse_domains(p.read_text(encoding="utf-8", errors="replace")) for p in paths))
    suite = RoutingTestSuite()
    resolvers = {
        cfg.stem: (lambda d, cfg=cfg: suite._resolve_json(cfg, d)) for cfg in sorted((REPO_ROOT / "HAPP").glob("*.JSON"))
    }
    found = find_direct(domains, resolvers, GeositeMatcher("allow-direct", ALLOW_DIRECT).matches)

    print("## Geoblocked domains routed DIRECT\n")
    print(f"Checked {len(domains)} domains from {', '.join(p.name for p in paths)} against HAPP/*.JSON.\n")
    for name, hits in found.items():
        print(f"- **{name}**: {', '.join(f'`{d}`' for d in hits) if hits else 'none'}")
    return 1 if any(found.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
