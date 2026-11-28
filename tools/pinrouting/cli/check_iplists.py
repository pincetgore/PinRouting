"""Sanity gates for the daily geoip build: a broken upstream list must stop the release, not reroute users."""

from __future__ import annotations

import argparse
import ipaddress
import re
from bisect import bisect_right
from pathlib import Path

from pinrouting.geoip import cidr_of_line

# Fixed floor of CIDRs per downloaded list, about half its 10.2026 size. It applies when the previous
# release has no count for the list or the list held under 1000 CIDRs: small lists swing too much for
# the half-of-previous rule. refiltercommunity has held 1..14 entries: non-empty only.
MIN_CIDRS = {
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
MAX_IPV4_ADDRESSES = {"direct": 80_000_000, "whitelist": 400_000}
# IPv4 addresses of whitelist.txt allowed outside the RU/BY geo lists and CUSTOM-WHITELIST.txt. The list
# comes from a third-party repo and goes DIRECT; in 11.2026 only 256 were outside (151.236.93.0/24).
MAX_WHITELIST_OUTSIDE_GEO = 4096
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


def _networks(text: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    cidrs = (cidr_of_line(line) for line in text.splitlines())
    return [ipaddress.ip_network(c, strict=False) for c in cidrs if c]


def check_built_list(name: str, text: str) -> list[str]:
    """Checks one text dump of the geoip builder (output/text/<name>.txt). Returns error messages."""
    nets = _networks(text)
    errors: list[str] = []
    total = sum(n.num_addresses for n in ipaddress.collapse_addresses(n for n in nets if isinstance(n, ipaddress.IPv4Network)))
    if total > MAX_IPV4_ADDRESSES[name]:
        errors.append(f"{name}.txt covers {total:,} IPv4 addresses, limit is {MAX_IPV4_ADDRESSES[name]:,}")
    for ip in MUST_NOT_CONTAIN:
        addr = ipaddress.ip_address(ip)
        hit = next((n for n in nets if addr in n), None)
        if hit:
            errors.append(f"{name}.txt would route {ip} DIRECT (via {hit})")
    return errors


def check_whitelist_geo(whitelist_text: str, geo_texts: list[str]) -> list[str]:
    """Checks that the built whitelist stays inside the RU/BY geo lists (and CUSTOM-WHITELIST.txt).

    shortcut: IPv4 only, like MAX_IPV4_ADDRESSES; check IPv6 too if the whitelist sources start shipping it.
    """
    geo = [n for text in geo_texts for n in _networks(text) if isinstance(n, ipaddress.IPv4Network)]
    cover = [(int(n.network_address), int(n.broadcast_address) + 1) for n in ipaddress.collapse_addresses(geo)]
    starts = [lo for lo, _ in cover]
    outside: list[tuple[int, ipaddress.IPv4Network]] = []
    wl = (n for n in _networks(whitelist_text) if isinstance(n, ipaddress.IPv4Network))
    for net in ipaddress.collapse_addresses(wl):
        lo, hi = int(net.network_address), int(net.broadcast_address) + 1
        i, inside = max(bisect_right(starts, lo) - 1, 0), 0  # cover is sorted and disjoint
        while i < len(cover) and cover[i][0] < hi:
            inside += max(0, min(hi, cover[i][1]) - max(lo, cover[i][0]))
            i += 1
        if inside < hi - lo:
            outside.append((hi - lo - inside, net))
    total = sum(count for count, _ in outside)
    if total <= MAX_WHITELIST_OUTSIDE_GEO:
        return []
    biggest = ", ".join(str(net) for _, net in sorted(outside, reverse=True)[:5])
    return [(
        f"whitelist.txt has {total:,} IPv4 addresses outside the RU/BY geo lists, limit is "
        f"{MAX_WHITELIST_OUTSIDE_GEO:,} (largest: {biggest}). They would go DIRECT, past the VPN."
    )]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pinrouting check-iplists", description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    downloads = sub.add_parser("downloads", help="check the downloaded lists, write list-counts.txt")
    downloads.add_argument("dir", type=Path, help="dir with the downloaded lists")
    downloads.add_argument("--prev", type=Path, help="list-counts.txt of the previous release")
    downloads.add_argument("--accept", action="store_true", help="skip the half-of-previous-release check")
    output = sub.add_parser("output", help="check the built direct.txt / whitelist.txt")
    output.add_argument("text_dir", type=Path, help="geoip builder output/text dir")
    output.add_argument("--whitelist-geo", type=Path, nargs="+", required=True,
                        help="RU/BY CIDR lists (and CUSTOM-WHITELIST.txt) the whitelist must stay inside")
    args = parser.parse_args(argv)

    if args.mode == "downloads":
        errors = check_downloads(args.dir, args.prev, args.accept)
    else:
        errors = []
        texts = {name: (args.text_dir / f"{name}.txt").read_text(encoding="utf-8") for name in MAX_IPV4_ADDRESSES}
        for name, text in texts.items():
            errors += check_built_list(name, text)
        geo = [path.read_text(encoding="utf-8") for path in args.whitelist_geo]
        errors += check_whitelist_geo(texts["whitelist"], geo)
    for err in errors:
        print(f"::error::{err}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
