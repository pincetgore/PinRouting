"""Single parser for geosite/data lines, matching v2fly/domain-list-community (the builder of geosite.dat).

Line format: [type:]value [@attr ...]  # comment   (type defaults to "domain")
"""

from __future__ import annotations

import re
from pathlib import Path

# v2fly validateDomainName: a-z0-9-, labels 1..63 chars not starting/ending with "-", total <= 253
_DOMAIN_RE = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))*")
_KEYWORD_RE = re.compile(r"[a-z0-9.-]+")


def split_rule(line: str) -> tuple[str, list[str]] | None:
    """Returns (type, fields) where fields[0] is the value and the rest are attributes, or None for blank/comment."""
    content = line.split("#", 1)[0].strip()
    if not content:
        return None
    typ, sep, rule = content.partition(":")
    if not sep:
        typ, rule = "domain", typ
    return typ.strip().lower(), rule.split()


def parse_rule(line: str) -> tuple[str, str] | None:
    """Returns (type, value) or None for blank/comment lines. Value is lowercased except for regexp."""
    parsed = split_rule(line)
    if parsed is None or not parsed[1]:
        return None
    typ, fields = parsed
    return typ, fields[0] if typ == "regexp" else fields[0].lower()


def is_valid_domain(value: str) -> bool:
    return len(value) <= 253 and _DOMAIN_RE.fullmatch(value) is not None


def is_valid_keyword(value: str) -> bool:
    return _KEYWORD_RE.fullmatch(value) is not None


def remove_domains(path: Path, domains: set[str]) -> int:
    """Deletes domain:/full: lines whose value is in `domains`; keeps everything else. Returns lines removed."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept: list[str] = []
    removed = 0
    for line in lines:
        rule = parse_rule(line)
        if rule and rule[0] in ("domain", "full") and rule[1] in domains:
            removed += 1
            continue
        # Collapse the blank line left behind into the previous one
        if not line.strip() and kept and not kept[-1].strip():
            continue
        kept.append(line)
    path.write_text("".join(kept).rstrip() + "\n", encoding="utf-8")
    return removed
