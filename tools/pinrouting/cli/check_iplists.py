"""Sanity gates for the daily geoip build: a broken upstream list must stop the release, not reroute users."""

from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path

# Fixed floor of CIDRs per downloaded list, about half its 10.2026 size. It applies when the previous
# release has no count for the list or the list held under 1000 CIDRs: small lists swing too much for
# the half-of-previous rule. refiltercommunity has held 1..14 entries: non-empty only.
MIN_CIDRS = {
    "whitelist.txt": 40,
    "antifilterdownloadcommunity.txt": 400,
    "refilter.txt": 10000,
    "refiltercommunity.txt": 1,
    "antifilternetwork.txt": 50000,
    "cdn.lst": 1500,
    "merged.sum": 9000,
    "ipinfo_ru.lst": 30000,
    "ipinfo_by.lst": 1000,
    "geolite_ru.lst": 6000,
    "dbip_ru.lst": 6000,
}
_CIDR = re.compile(r"[0-9a-fA-F:.]+/[0-9]+")

# IPv4 addresses a built list may cover. In 11.2026 direct covered 49.0M and whitelist 0.22M: one
# 0.0.0.0/0 line in an upstream "add" list would otherwise send nearly all traffic DIRECT, past the VPN.
MAX_IPV4_ADDRESSES = {"direct": 80_000_000, "whitelist": 1_000_000}
# Foreign addresses (Google DNS) that must never be routed DIRECT
MUST_NOT_CONTAIN = ("8.8.8.8", "2001:4860:4860::8888")


def check_download(name: str, text: str, last: int = 0) -> tuple[int, str | None]:
    """Checks one downloaded list; `last` is its CIDR count in the previous release. Returns (count, error).

    The list must start with a CIDR line and keep enough CIDRs: an empty, HTML or truncated "remove"
    list would silently route blocked IPs DIRECT. A list that had 1000+ CIDRs in the previous release
    must keep half of that, so the limit follows real changes.
    """
    lines = text.splitlines()
    first = next((ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")), "")
    if not _CIDR.fullmatch(first.rstrip()):
        return 0, f"Download {name} is empty or not a CIDR list (first line: '{first[:80]}')"
    count = sum(1 for ln in lines if _CIDR.match(ln))
    minimum, why = MIN_CIDRS[name], ""
    if last >= 1000:
        minimum, why = last // 2, f" (half of {last} in the previous release)"
    if count < minimum:
        return count, (
            f"Download {name} has {count} CIDRs, expected at least {minimum}{why}. Truncated upstream? "
            "If the drop is real, run this workflow by hand with accept_list_sizes."
        )
    return count, None


def check_downloads(directory: Path, prev_file: Path | None, accept: bool) -> list[str]:
    """Checks every list in MIN_CIDRS and writes list-counts.txt, the baseline for the next run."""
    prev: dict[str, int] = {}
    if accept:
        print("::warning::accept_list_sizes: today's list sizes become the new baseline")
    elif prev_file and prev_file.is_file() and (tokens := prev_file.read_text(encoding="utf-8").split()):
        prev = dict(zip(tokens[::2], map(int, tokens[1::2])))  # lines are "<file> <count>"
    else:
        print("::warning::No list-counts.txt in the release branch: only the fixed floors are checked")

    errors: list[str] = []
    counts: list[str] = []
    for name in MIN_CIDRS:
        text = (directory / name).read_text(encoding="utf-8", errors="replace")
        count, error = check_download(name, text, prev.get(name, 0))
        counts.append(f"{name} {count}\n")
        if error:
            errors.append(error)
    if not errors:
        (directory / "list-counts.txt").write_text("".join(counts), encoding="utf-8")
    return errors


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
    downloads = sub.add_parser("downloads", help="check the downloaded lists, write list-counts.txt")
    downloads.add_argument("dir", type=Path, help="dir with the downloaded lists")
    downloads.add_argument("--prev", type=Path, help="list-counts.txt of the previous release")
    downloads.add_argument("--accept", action="store_true", help="skip the half-of-previous-release check")
    output = sub.add_parser("output", help="check the built direct.txt / whitelist.txt")
    output.add_argument("text_dir", type=Path, help="geoip builder output/text dir")
    args = parser.parse_args(argv)

    if args.mode == "downloads":
        errors = check_downloads(args.dir, args.prev, args.accept)
    else:
        errors = []
        for name in MAX_IPV4_ADDRESSES:
            errors += check_built_list(name, (args.text_dir / f"{name}.txt").read_text(encoding="utf-8"))
    for err in errors:
        print(f"::error::{err}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
