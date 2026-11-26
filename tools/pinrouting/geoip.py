"""Single reader for lines of CIDR lists (geoip/*.txt, geoip builder text output, downloaded direct lists)."""

from __future__ import annotations


def cidr_of_line(line: str) -> str:
    """The CIDR text of one list line: everything before "#", stripped. "" for blank and comment lines."""
    return line.split("#", 1)[0].strip()
