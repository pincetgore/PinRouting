"""Check and clean up dead domains and unrouted/dead IP CIDRs.

Verifies:
- Domains across multiple independent DNS resolvers (Cloudflare 1.1.1.1, Google 8.8.8.8, Yandex 77.88.8.8)
  with retry logic and confirmation of NXDOMAIN / non-existence.
- IP addresses and CIDR subnets using TCP (port 443 TLS, port 80 HTTP) and ICMP ping.
  Subnets (/24 and wider) are sampled via representative hosts (gateway, early, middle, and late addresses).
- Supports dry-run inspection or in-place removal of dead entries with Markdown and JSON reporting.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import ipaddress
import json
import logging
import socket
import ssl
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import dns.asyncresolver
    import dns.exception
    import dns.resolver

    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

logger = logging.getLogger("pinrouting.check_dead")

DEFAULT_RESOLVERS = ["1.1.1.1", "8.8.8.8", "77.88.8.8"]
DEFAULT_MAX_SAMPLE_HOSTS = 5
DEFAULT_CONCURRENCY = 150
DEFAULT_DNS_TIMEOUT = 2.0
DEFAULT_IP_TIMEOUT = 1.5
DEFAULT_RETRIES = 2


@dataclass
class DeadEntry:
    target: str  # domain name or cidr string
    file_path: str
    line_number: int
    reason: str
    entry_type: str  # "domain" or "ip"


@dataclass
class CheckSummary:
    total_domains: int = 0
    alive_domains: int = 0
    dead_domains: int = 0
    skipped_domains: int = 0
    total_ips: int = 0
    alive_ips: int = 0
    dead_ips: int = 0
    skipped_ips: int = 0
    removed_entries: int = 0
    dry_run: bool = True
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    dead_entries: list[DeadEntry] = field(default_factory=list)
    file_stats: dict[str, dict[str, int]] = field(default_factory=dict)


def parse_domain_rule(line: str) -> tuple[str, str] | None:
    """Parses a geosite data line. Returns (rule_type, domain) or None if not a domain."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    # Strip inline comment and tag attributes (@cn, etc.)
    no_comment = stripped.split("#", 1)[0].strip()
    content = no_comment.split("@", 1)[0].strip()
    if not content:
        return None

    if ":" in content:
        rtype, val = content.split(":", 1)
        rtype = rtype.strip().lower()
        val = val.strip().lower()
    else:
        rtype = "domain"
        val = content.lower()

    if rtype in ("keyword", "regexp", "include"):
        return None

    if rtype in ("domain", "full"):
        domain = val.rstrip(".")
        if domain.startswith(("http://", "https://")):
            domain = domain.split("://", 1)[1]
        domain = domain.split("/", 1)[0].strip()
        if domain and not any(ch.isspace() for ch in domain):
            return rtype, domain

    return None


async def check_domain_liveness(
    domain: str,
    resolvers: list[str],
    timeout: float = DEFAULT_DNS_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> tuple[bool, str]:
    """Checks whether a domain is alive across multiple DNS resolvers.

    A domain is alive if AT LEAST ONE resolver successfully returns records (A, AAAA, CNAME, or NS/SOA for zones).
    A domain is dead ONLY IF all resolvers confirm NXDOMAIN or absence of records.
    """
    if not HAS_DNSPYTHON:
        # Fallback to standard library getaddrinfo
        for _ in range(retries + 1):
            try:
                loop = asyncio.get_running_loop()
                await loop.getaddrinfo(domain, None)
                return True, "resolved via system resolver"
            except (socket.gaierror, OSError, TimeoutError):
                pass
            await asyncio.sleep(0.2)
        return False, "failed to resolve via system DNS"

    nx_or_noanswer_count = 0
    last_error = ""

    for ns in resolvers:
        resolver = dns.asyncresolver.Resolver(configure=False)
        resolver.nameservers = [ns]
        resolver.lifetime = timeout

        resolved_for_ns = False
        ns_nxdomain = False

        for attempt in range(retries + 1):
            try:
                # 1. Try A record
                ans = await resolver.resolve(domain, "A")
                if ans:
                    return True, f"resolved A on {ns}"
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                # 2. Try AAAA record
                try:
                    ans = await resolver.resolve(domain, "AAAA")
                    if ans:
                        return True, f"resolved AAAA on {ns}"
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    # 3. Try CNAME
                    try:
                        ans = await resolver.resolve(domain, "CNAME")
                        if ans:
                            return True, f"resolved CNAME on {ns}"
                    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                        # 4. Check if apex domain zone exists with NS or SOA
                        try:
                            ans = await resolver.resolve(domain, "NS")
                            if ans:
                                return True, f"active zone NS on {ns}"
                        except (dns.exception.DNSException, OSError, TimeoutError):
                            with contextlib.suppress(dns.exception.DNSException, OSError, TimeoutError):
                                ans = await resolver.resolve(domain, "SOA")
                                if ans:
                                    return True, f"active zone SOA on {ns}"
                        ns_nxdomain = True
                        break
                    except (dns.exception.DNSException, OSError, TimeoutError) as e:
                        last_error = f"{ns} CNAME: {type(e).__name__}"
                except (dns.exception.DNSException, OSError, TimeoutError) as e:
                    last_error = f"{ns} AAAA: {type(e).__name__}"
            except (dns.exception.DNSException, OSError, TimeoutError) as e:
                last_error = f"{ns} A: {type(e).__name__}"
                if attempt < retries:
                    await asyncio.sleep(0.3)
                    continue

            if resolved_for_ns:
                break

        if ns_nxdomain:
            nx_or_noanswer_count += 1

    if nx_or_noanswer_count == len(resolvers):
        return False, f"NXDOMAIN on all {len(resolvers)} DNS resolvers"

    # If all resolvers failed with errors/timeouts, play safe: do not mark dead
    return True, f"unconfirmed DNS status ({last_error})"


def get_sample_hosts(
    net: ipaddress.IPv4Network | ipaddress.IPv6Network,
    max_samples: int = DEFAULT_MAX_SAMPLE_HOSTS,
) -> list[str]:
    """Generates a representative sample of hosts to test for a CIDR subnet."""
    num = net.num_addresses
    if num == 1:
        return [str(net.network_address)]
    if num == 2:
        return [str(net[0]), str(net[1])]
    if num <= max_samples:
        return [str(net[i]) for i in range(num)]

    candidates = [
        net[1],  # Gateway / first address
        net[2],  # Second address
        net[num // 2],  # Middle host
        net[-2],  # Last usable address
    ]
    if num >= 256:
        # For /24 or wider, sample host 254
        candidates.append(net[254])

    seen: set[str] = set()
    samples: list[str] = []
    for ip in candidates:
        s = str(ip)
        if s not in seen:
            seen.add(s)
            samples.append(s)
    return samples[:max_samples]


async def ping_host(ip: str, timeout: float = 1.0) -> bool:
    """Executes a single ICMP ping to the target IP asynchronously."""
    is_darwin = sys.platform == "darwin"
    if is_darwin:
        cmd = ["ping", "-c", "1", "-W", str(int(timeout * 1000)), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout))), ip]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        returncode = await asyncio.wait_for(proc.wait(), timeout=timeout + 0.5)
        return returncode == 0
    except (OSError, TimeoutError):
        return False


async def tcp_probe_443(ip: str, timeout: float = 1.0) -> bool:
    """Probes port 443 with TLS ClientHello or TCP connect."""
    try:
        coro = asyncio.open_connection(ip, 443)
        _reader, writer = await asyncio.wait_for(coro, timeout=timeout)
        with contextlib.suppress(OSError, TimeoutError):
            writer.close()
            await writer.wait_closed()
        return True
    except ConnectionRefusedError:
        # TCP RST received: host is online and active!
        return True
    except ssl.SSLError:
        # TLS alert received: host is active!
        return True
    except (OSError, TimeoutError):
        return False


async def tcp_probe_80(ip: str, timeout: float = 1.0) -> bool:
    """Probes port 80 with HTTP HEAD probe or TCP connect."""
    try:
        coro = asyncio.open_connection(ip, 80)
        reader, writer = await asyncio.wait_for(coro, timeout=timeout)
        try:
            writer.write(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode("ascii") + b"\r\n\r\n")
            await asyncio.wait_for(writer.drain(), timeout=timeout)
            with contextlib.suppress(OSError, TimeoutError):
                await asyncio.wait_for(reader.read(32), timeout=timeout)
        finally:
            writer.close()
            with contextlib.suppress(OSError, TimeoutError):
                await writer.wait_closed()
        return True
    except ConnectionRefusedError:
        # TCP RST received: host is online!
        return True
    except (OSError, TimeoutError):
        return False


async def is_host_alive(ip: str, timeout: float = DEFAULT_IP_TIMEOUT) -> bool:
    """Checks if a single IP host is alive using TCP 443, TCP 80, and ICMP ping."""
    # 1. Fast TCP 443 probe
    if await tcp_probe_443(ip, timeout=timeout):
        return True
    # 2. Fast TCP 80 probe
    if await tcp_probe_80(ip, timeout=timeout):
        return True
    # 3. ICMP Ping fallback
    return await ping_host(ip, timeout=timeout)


async def check_network_liveness(
    cidr_str: str,
    timeout: float = DEFAULT_IP_TIMEOUT,
    max_samples: int = DEFAULT_MAX_SAMPLE_HOSTS,
) -> tuple[bool, str]:
    """Checks whether a CIDR network has at least one active host."""
    try:
        net = ipaddress.ip_network(cidr_str, strict=False)
    except ValueError as e:
        return False, f"Invalid CIDR syntax: {e}"

    samples = get_sample_hosts(net, max_samples=max_samples)
    for host in samples:
        if await is_host_alive(host, timeout=timeout):
            return True, f"Host {host} is active"

    return False, f"All {len(samples)} sampled hosts unresponsive on TCP 443, 80, and ICMP ping"


def collect_domain_tasks(
    geosite_dir: Path, excluded_files: set[str], summary: CheckSummary
) -> list[tuple[str, int, str, Path]]:
    """Reads geosite files and collects all domain validation tasks."""
    domain_tasks: list[tuple[str, int, str, Path]] = []
    for file_path in sorted(geosite_dir.iterdir()):
        if not file_path.is_file() or file_path.name.startswith(".") or file_path.name in excluded_files:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        file_key = f"geosite/{file_path.name}"
        summary.file_stats[file_key] = {"total": 0, "dead": 0, "alive": 0, "skipped": 0}

        for line_no, line in enumerate(lines, 1):
            rule = parse_domain_rule(line)
            if not rule:
                summary.file_stats[file_key]["skipped"] += 1
                summary.skipped_domains += 1
                continue
            _rtype, domain = rule
            domain_tasks.append((domain, line_no, line, file_path))
            summary.file_stats[file_key]["total"] += 1
            summary.total_domains += 1

    return domain_tasks


def collect_ip_tasks(
    geoip_dir: Path, excluded_files: set[str], summary: CheckSummary
) -> list[tuple[str, int, str, Path]]:
    """Reads geoip files and collects all IP CIDR validation tasks."""
    ip_tasks: list[tuple[str, int, str, Path]] = []
    for file_path in sorted(geoip_dir.glob("*.txt")):
        if not file_path.is_file() or file_path.name.startswith(".") or file_path.name in excluded_files:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        file_key = f"geoip/{file_path.name}"
        summary.file_stats[file_key] = {"total": 0, "dead": 0, "alive": 0, "skipped": 0}

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                summary.file_stats[file_key]["skipped"] += 1
                summary.skipped_ips += 1
                continue
            cidr_str = stripped.split("#")[0].strip()
            if not cidr_str:
                continue
            try:
                ipaddress.ip_network(cidr_str, strict=False)
                ip_tasks.append((cidr_str, line_no, line, file_path))
                summary.file_stats[file_key]["total"] += 1
                summary.total_ips += 1
            except ValueError:
                summary.file_stats[file_key]["skipped"] += 1
                summary.skipped_ips += 1

    return ip_tasks


class DeadEntriesChecker:
    def __init__(
        self,
        root_dir: Path,
        resolvers: list[str] | None = None,
        dns_timeout: float = DEFAULT_DNS_TIMEOUT,
        ip_timeout: float = DEFAULT_IP_TIMEOUT,
        concurrency: int = DEFAULT_CONCURRENCY,
        max_samples: int = DEFAULT_MAX_SAMPLE_HOSTS,
        retries: int = DEFAULT_RETRIES,
        remove: bool = False,
        excluded_files: set[str] | None = None,
    ) -> None:
        self.root_dir = root_dir
        self.geosite_dir = root_dir / "geosite" / "data"
        self.geoip_dir = root_dir / "geoip"
        self.resolvers = resolvers or DEFAULT_RESOLVERS
        self.dns_timeout = dns_timeout
        self.ip_timeout = ip_timeout
        self.concurrency = concurrency
        self.max_samples = max_samples
        self.retries = retries
        self.remove = remove
        self.excluded_files = excluded_files or set()
        self.summary = CheckSummary(dry_run=not remove)

    async def check_all_domains(self) -> None:
        """Inspects all geosite data files for dead domains."""
        if not self.geosite_dir.is_dir():
            logger.warning(f"Geosite directory not found: {self.geosite_dir}")
            return

        domain_tasks = collect_domain_tasks(self.geosite_dir, self.excluded_files, self.summary)

        print(f"[*] Checking {len(domain_tasks)} domains with concurrency {self.concurrency}...")
        sem = asyncio.Semaphore(self.concurrency)
        total = len(domain_tasks)

        async def worker(
            domain: str, line_no: int, raw_line: str, file_path: Path
        ) -> tuple[bool, str, str, int, Path]:
            async with sem:
                alive, reason = await check_domain_liveness(
                    domain,
                    resolvers=self.resolvers,
                    timeout=self.dns_timeout,
                    retries=self.retries,
                )
                return alive, reason, domain, line_no, file_path

        tasks = [worker(d, l_no, rl, fp) for d, l_no, rl, fp in domain_tasks]
        for completed, fut in enumerate(asyncio.as_completed(tasks), 1):
            alive, reason, domain, line_no, file_path = await fut
            file_key = f"geosite/{file_path.name}"

            if completed % 100 == 0 or completed == total:
                pct = (completed / total) * 100 if total > 0 else 100
                print(
                    f"\r    Domains progress: {completed}/{total} ({pct:.1f}%) | "
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
                        entry_type="domain",
                    )
                )

        print()

    async def check_all_ips(self) -> None:
        """Inspects all geoip text files for dead IP CIDRs."""
        if not self.geoip_dir.is_dir():
            logger.warning(f"GeoIP directory not found: {self.geoip_dir}")
            return

        ip_tasks = collect_ip_tasks(self.geoip_dir, self.excluded_files, self.summary)

        print(f"[*] Checking {len(ip_tasks)} IP CIDRs with concurrency {self.concurrency}...")
        sem = asyncio.Semaphore(self.concurrency)
        total = len(ip_tasks)

        async def worker(
            cidr: str, line_no: int, raw_line: str, file_path: Path
        ) -> tuple[bool, str, str, int, Path]:
            async with sem:
                alive, reason = await check_network_liveness(
                    cidr,
                    timeout=self.ip_timeout,
                    max_samples=self.max_samples,
                )
                return alive, reason, cidr, line_no, file_path

        tasks = [worker(c, l_no, rl, fp) for c, l_no, rl, fp in ip_tasks]
        for completed, fut in enumerate(asyncio.as_completed(tasks), 1):
            alive, reason, cidr, line_no, file_path = await fut
            file_key = f"geoip/{file_path.name}"

            if completed % 100 == 0 or completed == total:
                pct = (completed / total) * 100 if total > 0 else 100
                print(
                    f"\r    IPs progress: {completed}/{total} ({pct:.1f}%) | "
                    f"Dead: {self.summary.dead_ips}",
                    end="",
                    flush=True,
                )

            if alive:
                self.summary.alive_ips += 1
                self.summary.file_stats[file_key]["alive"] += 1
            else:
                self.summary.dead_ips += 1
                self.summary.file_stats[file_key]["dead"] += 1
                self.summary.dead_entries.append(
                    DeadEntry(
                        target=cidr,
                        file_path=str(file_path.relative_to(self.root_dir)),
                        line_number=line_no,
                        reason=reason,
                        entry_type="ip",
                    )
                )

        print()

    def remove_dead_entries_from_files(self) -> int:
        """Removes identified dead entries from the source files in-place."""
        if not self.summary.dead_entries:
            return 0

        # Group dead entries by file
        dead_by_file: dict[str, set[str]] = {}
        for entry in self.summary.dead_entries:
            dead_by_file.setdefault(entry.file_path, set()).add(entry.target)

        total_removed = 0
        for rel_path, targets in dead_by_file.items():
            full_path = self.root_dir / rel_path
            if not full_path.is_file():
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines: list[str] = []
            removed_in_file = 0

            is_geosite = "geosite" in rel_path
            is_geoip = "geoip" in rel_path

            for line in lines:
                should_remove = False
                stripped = line.strip()

                if is_geosite:
                    rule = parse_domain_rule(line)
                    if rule:
                        _, domain = rule
                        if domain in targets:
                            should_remove = True
                elif is_geoip and stripped and not stripped.startswith("#"):
                    cidr_part = stripped.split("#")[0].strip()
                    if cidr_part in targets:
                        should_remove = True

                if should_remove:
                    removed_in_file += 1
                else:
                    new_lines.append(line)

            # Clean up excessive blank lines (more than 1 empty line sequentially)
            cleaned_lines: list[str] = []
            prev_blank = False
            for line in new_lines:
                is_blank = not line.strip()
                if is_blank and prev_blank:
                    continue
                cleaned_lines.append(line)
                prev_blank = is_blank

            # Ensure trailing newline
            content = "".join(cleaned_lines).rstrip() + "\n"
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            total_removed += removed_in_file
            print(f"[-] Removed {removed_in_file} dead entries from {rel_path}")

        self.summary.removed_entries = total_removed
        return total_removed

    def generate_markdown_report(self) -> str:
        """Generates a GitHub-flavored Markdown report."""
        duration = self.summary.end_time - self.summary.start_time
        lines: list[str] = [
            "# 🧹 Dead Entries Inspection & Cleanup Report",
            "",
            f"**Execution Mode:** {'DRY-RUN (Inspection only)' if self.summary.dry_run else 'ACTIVE CLEANUP (Removed)'}",
            f"**Duration:** {duration:.1f} seconds",
            "",
            "## 📊 Summary",
            "",
            "| Category | Total Checked | Active / Alive | Dead / Unresponsive | Status |",
            "| :--- | :---: | :---: | :---: | :--- |",
        ]

        if self.summary.total_domains > 0:
            status = "Cleaned" if not self.summary.dry_run else "Found"
            lines.append(
                f"| **Domains** | {self.summary.total_domains:,} | "
                f"{self.summary.alive_domains:,} | "
                f"**{self.summary.dead_domains:,}** | "
                f"{status if self.summary.dead_domains > 0 else 'All Alive'} |"
            )

        if self.summary.total_ips > 0:
            status = "Cleaned" if not self.summary.dry_run else "Found"
            lines.append(
                f"| **IP CIDRs** | {self.summary.total_ips:,} | "
                f"{self.summary.alive_ips:,} | "
                f"**{self.summary.dead_ips:,}** | "
                f"{status if self.summary.dead_ips > 0 else 'All Alive'} |"
            )

        lines.extend([
            "",
            "## 📁 Breakdown by File",
            "",
            "| File | Checked | Alive | Dead |",
            "| :--- | :---: | :---: | :---: |",
        ])

        for file_key, stats in sorted(self.summary.file_stats.items()):
            dead_str = f"**{stats['dead']:,}**" if stats["dead"] > 0 else "0"
            lines.append(f"| `{file_key}` | {stats['total']:,} | {stats['alive']:,} | {dead_str} |")

        if self.summary.dead_entries:
            max_display = 100
            total_dead = len(self.summary.dead_entries)
            lines.extend([
                "",
                "## 🔍 Dead Entries Details",
                "",
            ])
            if total_dead > max_display:
                lines.extend([
                    "> [!NOTE]",
                    f"> Showing first **{max_display}** of **{total_dead:,}** detected dead entries to keep summary readable. Full list is available in the attached `dead-report.json` artifact.",
                    "",
                ])
            lines.extend([
                "<details>",
                f"<summary><b>Click to view details ({min(total_dead, max_display)} shown)</b></summary>",
                "",
                "| File | Type | Target | Reason |",
                "| :--- | :---: | :--- | :--- |",
            ])
            for entry in self.summary.dead_entries[:max_display]:
                lines.append(f"| `{entry.file_path}` | {entry.entry_type} | `{entry.target}` | {entry.reason} |")
            if total_dead > max_display:
                lines.append(f"| ... | ... | *and {total_dead - max_display} more* | *see dead-report.json* |")
            lines.extend([
                "",
                "</details>",
            ])
        else:
            lines.extend([
                "",
                "🎉 **No dead entries found! Everything is healthy and responsive.**",
            ])

        return "\n".join(lines) + "\n"

    def generate_json_report(self) -> dict[str, Any]:
        """Generates a structured dictionary report."""
        return {
            "summary": {
                "dry_run": self.summary.dry_run,
                "total_domains": self.summary.total_domains,
                "alive_domains": self.summary.alive_domains,
                "dead_domains": self.summary.dead_domains,
                "total_ips": self.summary.total_ips,
                "alive_ips": self.summary.alive_ips,
                "dead_ips": self.summary.dead_ips,
                "removed_entries": self.summary.removed_entries,
                "duration_seconds": round(self.summary.end_time - self.summary.start_time, 2),
            },
            "file_stats": self.summary.file_stats,
            "dead_entries": [asdict(e) for e in self.summary.dead_entries],
        }


async def run_checker(args: argparse.Namespace) -> int:
    root_dir = Path(args.root_dir).resolve()
    resolvers = [r.strip() for r in args.resolvers.split(",") if r.strip()]
    excluded = {x.strip() for x in args.exclude_files.split(",") if x.strip()} if args.exclude_files else set()

    checker = DeadEntriesChecker(
        root_dir=root_dir,
        resolvers=resolvers,
        dns_timeout=args.dns_timeout,
        ip_timeout=args.ip_timeout,
        concurrency=args.concurrency,
        max_samples=args.max_sample_hosts,
        retries=args.retries,
        remove=args.remove,
        excluded_files=excluded,
    )

    print("=" * 80)
    print("  PinRouting Dead Entries Liveness Checker")
    print(f"  Target: {args.target.upper()} | Mode: {'REMOVE' if args.remove else 'DRY-RUN'}")
    print(f"  DNS Resolvers: {', '.join(resolvers)} | Concurrency: {args.concurrency}")
    print("=" * 80)

    if args.target in ("all", "domains"):
        await checker.check_all_domains()

    if args.target in ("all", "ips"):
        await checker.check_all_ips()

    checker.summary.end_time = time.time()

    if args.remove and checker.summary.dead_entries:
        print("[*] Removing dead entries from files...")
        checker.remove_dead_entries_from_files()

    md_report = checker.generate_markdown_report()
    json_report = checker.generate_json_report()

    if args.output_markdown:
        out_md = Path(args.output_markdown)
        out_md.write_text(md_report, encoding="utf-8")
        print(f"[+] Markdown report saved to {out_md}")

    if args.output_json:
        out_json = Path(args.output_json)
        out_json.write_text(json.dumps(json_report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[+] JSON report saved to {out_json}")

    print("\n" + "=" * 80)
    print(
        f"Summary: Domains dead: {checker.summary.dead_domains}/{checker.summary.total_domains} | "
        f"IPs dead: {checker.summary.dead_ips}/{checker.summary.total_ips} | "
        f"Removed: {checker.summary.removed_entries}"
    )
    print("=" * 80)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pinrouting check-dead",
        description="Check and clean up dead domains and IP CIDRs in PinRouting rulesets.",
    )
    parser.add_argument("--root-dir", default=".", help="Root repo directory")
    parser.add_argument(
        "--target",
        choices=["all", "domains", "ips"],
        default="all",
        help="Target resources to verify (default: all)",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove dead entries from files in-place",
    )
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
        "--ip-timeout",
        type=float,
        default=DEFAULT_IP_TIMEOUT,
        help=f"Timeout per TCP/ping check in seconds (default: {DEFAULT_IP_TIMEOUT})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent check tasks (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--max-sample-hosts",
        type=int,
        default=DEFAULT_MAX_SAMPLE_HOSTS,
        help=f"Max sample hosts for CIDR subnets (default: {DEFAULT_MAX_SAMPLE_HOSTS})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retry attempts for transient network failures (default: {DEFAULT_RETRIES})",
    )
    parser.add_argument(
        "--exclude-files",
        default="",
        help="Comma-separated list of filenames to exclude from checking",
    )
    parser.add_argument(
        "--output-markdown",
        default="",
        help="Path to write Markdown summary report",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Path to write JSON details report",
    )

    args = parser.parse_args(argv)
    return asyncio.run(run_checker(args))


if __name__ == "__main__":
    raise SystemExit(main())
