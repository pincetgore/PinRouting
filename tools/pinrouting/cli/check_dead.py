"""Check and clean up dead domains in geosite/data.

A domain is dead only if every DNS resolver (Cloudflare 1.1.1.1, Google 8.8.8.8, Yandex 77.88.8.8)
answers NXDOMAIN; errors and timeouts count as alive. Supports dry-run inspection or in-place
removal with Markdown and JSON reporting.

IP lists are not checked: many hosts (APNs, RU-only services) ignore probes from foreign CI runners,
so "no answer" does not mean "unused".
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver
from pinrouting.geosite import parse_rule, remove_domains

DEFAULT_RESOLVERS = ["1.1.1.1", "8.8.8.8", "77.88.8.8"]
DEFAULT_CONCURRENCY = 150
DEFAULT_DNS_TIMEOUT = 2.0
DEFAULT_RETRIES = 2
DEFAULT_EXCLUDED_FILES = ["private"]
# Probed under a suffix rule before calling it dead: some authoritative servers answer NXDOMAIN for an empty
# non-terminal (xmpush.xiaomi.com) although names below it resolve (api.xmpush.xiaomi.com)
SUBDOMAIN_PROBES = ("www", "api")


@dataclass
class DeadEntry:
    target: str
    file_path: str
    line_number: int
    reason: str


@dataclass
class CheckSummary:
    total_domains: int = 0
    alive_domains: int = 0
    dead_domains: int = 0
    removed_entries: int = 0
    dry_run: bool = True
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    dead_entries: list[DeadEntry] = field(default_factory=list)
    file_stats: dict[str, dict[str, int]] = field(default_factory=dict)


async def check_domain_liveness(
    domain: str,
    resolvers: list[str],
    timeout: float = DEFAULT_DNS_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    suffix: bool = False,
) -> tuple[bool, str]:
    """Checks whether a domain is alive across multiple DNS resolvers.

    A domain is dead ONLY IF every resolver answers NXDOMAIN. NoAnswer (name exists, no A record) is
    alive: `domain:cdn.example.com` may have no A record while `img.cdn.example.com` does. RFC 8020 says
    NXDOMAIN also rules out subdomains, but not every server follows it, so a suffix rule is dead only
    if the SUBDOMAIN_PROBES names below it are dead too.
    """
    nxdomain_count = 0
    last_error = ""

    for ns in resolvers:
        resolver = dns.asyncresolver.Resolver(configure=False)
        resolver.nameservers = [ns]
        resolver.lifetime = timeout

        for attempt in range(retries + 1):
            try:
                await resolver.resolve(domain, "A")
                return True, f"resolved A on {ns}"
            except dns.resolver.NoAnswer:
                return True, f"name exists on {ns} (no A record)"
            except dns.resolver.NXDOMAIN:
                nxdomain_count += 1
                break
            except (dns.exception.DNSException, OSError) as e:
                last_error = f"{ns}: {type(e).__name__}"
                if attempt < retries:
                    await asyncio.sleep(0.3)

    if nxdomain_count == len(resolvers):
        for label in SUBDOMAIN_PROBES if suffix else ():
            alive, reason = await check_domain_liveness(f"{label}.{domain}", resolvers, timeout, retries)
            if alive:
                return True, f"{label}.{domain}: {reason}"
        return False, f"NXDOMAIN on all {len(resolvers)} DNS resolvers"

    # Some resolvers failed with errors/timeouts: play safe, do not mark dead
    return True, f"unconfirmed DNS status ({last_error})"


def collect_domain_tasks(
    geosite_dir: Path, excluded_files: set[str], summary: CheckSummary
) -> list[tuple[str, int, Path, bool]]:
    """Reads geosite files and collects (domain, line number, file, is suffix rule) for every domain:/full: rule."""
    domain_tasks: list[tuple[str, int, Path, bool]] = []
    for file_path in sorted(geosite_dir.iterdir()):
        if not file_path.is_file() or file_path.name.startswith(".") or file_path.name in excluded_files:
            continue

        file_key = f"geosite/{file_path.name}"
        summary.file_stats[file_key] = {"total": 0, "dead": 0, "alive": 0}

        with open(file_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                rule = parse_rule(line)
                if not rule or rule[0] not in ("domain", "full"):
                    continue
                domain_tasks.append((rule[1], line_no, file_path, rule[0] == "domain"))
                summary.file_stats[file_key]["total"] += 1
                summary.total_domains += 1

    return domain_tasks


class DeadEntriesChecker:
    def __init__(
        self,
        root_dir: Path,
        resolvers: list[str] | None = None,
        dns_timeout: float = DEFAULT_DNS_TIMEOUT,
        concurrency: int = DEFAULT_CONCURRENCY,
        retries: int = DEFAULT_RETRIES,
        remove: bool = False,
        excluded_files: set[str] | None = None,
    ) -> None:
        self.root_dir = root_dir
        self.geosite_dir = root_dir / "geosite" / "data"
        self.resolvers = resolvers or DEFAULT_RESOLVERS
        self.dns_timeout = dns_timeout
        self.concurrency = concurrency
        self.retries = retries
        self.excluded_files = excluded_files if excluded_files is not None else set(DEFAULT_EXCLUDED_FILES)
        self.summary = CheckSummary(dry_run=not remove)

    async def check_all_domains(self) -> None:
        """Inspects all geosite data files for dead domains."""
        domain_tasks = collect_domain_tasks(self.geosite_dir, self.excluded_files, self.summary)

        print(f"[*] Checking {len(domain_tasks)} domains with concurrency {self.concurrency}...")
        sem = asyncio.Semaphore(self.concurrency)
        total = len(domain_tasks)

        async def worker(domain: str, line_no: int, file_path: Path, suffix: bool) -> tuple[bool, str, str, int, Path]:
            async with sem:
                alive, reason = await check_domain_liveness(
                    domain,
                    resolvers=self.resolvers,
                    timeout=self.dns_timeout,
                    retries=self.retries,
                    suffix=suffix,
                )
                return alive, reason, domain, line_no, file_path

        tasks = [worker(*t) for t in domain_tasks]
        for completed, fut in enumerate(asyncio.as_completed(tasks), 1):
            alive, reason, domain, line_no, file_path = await fut
            file_key = f"geosite/{file_path.name}"

            if completed % 100 == 0 or completed == total:
                print(
                    f"\r    Domains progress: {completed}/{total} ({completed / total * 100:.1f}%) | "
                    f"Dead: {self.summary.dead_domains}",
                    end="",
                    flush=True,
                )

            if alive:
                self.summary.alive_domains += 1
                self.summary.file_stats[file_key]["alive"] += 1
            else:
                self.summary.dead_domains += 1
                self.summary.file_stats[file_key]["dead"] += 1
                self.summary.dead_entries.append(
                    DeadEntry(
                        target=domain,
                        file_path=str(file_path.relative_to(self.root_dir)),
                        line_number=line_no,
                        reason=reason,
                    )
                )

        print()

    def remove_dead_entries_from_files(self) -> int:
        """Removes dead domains from the geosite files in-place."""
        dead_by_file: dict[str, set[str]] = {}
        for entry in self.summary.dead_entries:
            dead_by_file.setdefault(entry.file_path, set()).add(entry.target)

        total_removed = 0
        for rel_path, targets in dead_by_file.items():
            removed = remove_domains(self.root_dir / rel_path, targets)
            total_removed += removed
            print(f"[-] Removed {removed} dead entries from {rel_path}")

        self.summary.removed_entries = total_removed
        return total_removed

    def generate_markdown_report(self) -> str:
        """Generates a GitHub-flavored Markdown report."""
        s = self.summary
        status = ("Cleaned" if not s.dry_run else "Found") if s.dead_domains else "All Alive"
        lines: list[str] = [
            "# 🧹 Dead Domains Inspection & Cleanup Report",
            "",
            f"**Execution Mode:** {'DRY-RUN (Inspection only)' if s.dry_run else 'ACTIVE CLEANUP (Removed)'}",
            f"**Duration:** {s.end_time - s.start_time:.1f} seconds",
            "",
            "## 📊 Summary",
            "",
            "| Category | Total Checked | Alive | Dead | Status |",
            "| :--- | :---: | :---: | :---: | :--- |",
            f"| **Domains** | {s.total_domains:,} | {s.alive_domains:,} | **{s.dead_domains:,}** | {status} |",
            "",
            "## 📁 Breakdown by File",
            "",
            "| File | Checked | Alive | Dead |",
            "| :--- | :---: | :---: | :---: |",
        ]

        for file_key, stats in sorted(s.file_stats.items()):
            dead_str = f"**{stats['dead']:,}**" if stats["dead"] > 0 else "0"
            lines.append(f"| `{file_key}` | {stats['total']:,} | {stats['alive']:,} | {dead_str} |")

        if s.dead_entries:
            max_display = 100
            total_dead = len(s.dead_entries)
            lines.extend(["", "## 🔍 Dead Domains Details", ""])
            if total_dead > max_display:
                lines.extend([
                    "> [!NOTE]",
                    (
                        f"> Showing first **{max_display}** of **{total_dead:,}** dead domains. "
                        "Full list is available in the attached `dead-report.json` artifact."
                    ),
                    "",
                ])
            lines.extend([
                "<details>",
                f"<summary><b>Click to view details ({min(total_dead, max_display)} shown)</b></summary>",
                "",
                "| File | Domain | Reason |",
                "| :--- | :--- | :--- |",
            ])
            for entry in s.dead_entries[:max_display]:
                lines.append(f"| `{entry.file_path}` | `{entry.target}` | {entry.reason} |")
            if total_dead > max_display:
                lines.append(f"| ... | *and {total_dead - max_display} more* | *see dead-report.json* |")
            lines.extend(["", "</details>"])
        else:
            lines.extend(["", "🎉 **No dead domains found!**"])

        return "\n".join(lines) + "\n"

    def generate_json_report(self) -> dict[str, Any]:
        """Generates a structured dictionary report."""
        s = self.summary
        return {
            "summary": {
                "dry_run": s.dry_run,
                "total_domains": s.total_domains,
                "alive_domains": s.alive_domains,
                "dead_domains": s.dead_domains,
                "removed_entries": s.removed_entries,
                "duration_seconds": round(s.end_time - s.start_time, 2),
            },
            "file_stats": s.file_stats,
            "dead_entries": [asdict(e) for e in s.dead_entries],
        }


async def run_checker(args: argparse.Namespace) -> int:
    root_dir = Path(args.root_dir).resolve()
    resolvers = [r.strip() for r in args.resolvers.split(",") if r.strip()]
    excluded = {x.strip() for x in args.exclude_files.split(",") if x.strip()}

    checker = DeadEntriesChecker(
        root_dir=root_dir,
        resolvers=resolvers,
        dns_timeout=args.dns_timeout,
        concurrency=args.concurrency,
        retries=args.retries,
        remove=args.remove,
        excluded_files=excluded,
    )

    print("=" * 80)
    print("  PinRouting Dead Domains Checker")
    print(f"  Mode: {'REMOVE' if args.remove else 'DRY-RUN'}")
    print(f"  DNS Resolvers: {', '.join(resolvers)} | Concurrency: {args.concurrency}")
    print("=" * 80)

    await checker.check_all_domains()
    checker.summary.end_time = time.time()

    if args.remove and checker.summary.dead_domains:
        print("[*] Removing dead domains from files...")
        checker.remove_dead_entries_from_files()

    if args.output_markdown:
        out_md = Path(args.output_markdown)
        out_md.write_text(checker.generate_markdown_report(), encoding="utf-8")
        print(f"[+] Markdown report saved to {out_md}")

    if args.output_json:
        out_json = Path(args.output_json)
        out_json.write_text(json.dumps(checker.generate_json_report(), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[+] JSON report saved to {out_json}")

    print("\n" + "=" * 80)
    print(
        f"Summary: Domains dead: {checker.summary.dead_domains}/{checker.summary.total_domains} | "
        f"Removed: {checker.summary.removed_entries}"
    )
    print("=" * 80)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pinrouting check-dead",
        description="Check and clean up dead domains in PinRouting geosite data.",
    )
    parser.add_argument("--root-dir", default=".", help="Root repo directory")
    parser.add_argument("--remove", action="store_true", help="Remove dead domains from files in-place")
    parser.add_argument(
        "--resolvers",
        default=",".join(DEFAULT_RESOLVERS),
        help=f"Comma-separated DNS resolvers (default: {','.join(DEFAULT_RESOLVERS)})",
    )
    parser.add_argument(
        "--dns-timeout",
        type=float,
        default=DEFAULT_DNS_TIMEOUT,
        help=f"Timeout per DNS query in seconds (default: {DEFAULT_DNS_TIMEOUT})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent check tasks (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retry attempts for transient network failures (default: {DEFAULT_RETRIES})",
    )
    parser.add_argument(
        "--exclude-files",
        default=",".join(DEFAULT_EXCLUDED_FILES),
        help=f"Comma-separated geosite filenames to skip (default: {','.join(DEFAULT_EXCLUDED_FILES)})",
    )
    parser.add_argument("--output-markdown", default="", help="Path to write Markdown summary report")
    parser.add_argument("--output-json", default="", help="Path to write JSON details report")

    args = parser.parse_args(argv)
    return asyncio.run(run_checker(args))


if __name__ == "__main__":
    raise SystemExit(main())
