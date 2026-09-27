"""Shadowrocket emitter: generates rules/*.list and *.CONF files with 100% legacy fidelity."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from pinrouting.emitters.base import BaseEmitter
from pinrouting.models import ProfileConfig


class ShadowrocketEmitter(BaseEmitter):
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.geosite_data_dir = root_dir / "geosite" / "data"
        self.geoip_dir = root_dir / "geoip"
        self.rules_dir = root_dir / "SHADOWROCKET" / "rules"

    def convert_domain_rule(self, line: str) -> Optional[str]:
        line = line.strip()
        if not line:
            return None

        # Pass through full-line comments and section headers as-is
        if line.startswith("#"):
            return line

        # Parse directives: domain:example.com, full:example.com, keyword:example, regexp:...
        if line.startswith("full:"):
            domain = line.split(":", 1)[1].strip()
            return f"DOMAIN,{domain}"
        elif line.startswith("domain:"):
            domain = line.split(":", 1)[1].strip()
            return f"DOMAIN-SUFFIX,{domain}"
        elif line.startswith("keyword:"):
            kw = line.split(":", 1)[1].strip()
            return f"DOMAIN-KEYWORD,{kw}"
        elif line.startswith("regexp:"):
            pattern = line.split(":", 1)[1].strip()
            return f"URL-REGEX,{pattern}"
        elif ":" in line:
            parts = line.split(":", 1)
            prefix, domain = parts[0].strip(), parts[1].strip()
            if prefix == "include":
                return None
            return f"DOMAIN-SUFFIX,{domain}"
        else:
            return f"DOMAIN-SUFFIX,{line}"

    def build_ruleset_file(
        self, src_path: Path, dst_path: Path, repo: str, updated_str: str
    ) -> int:
        out_lines: List[str] = []
        rule_count = 0

        with open(src_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                converted = self.convert_domain_rule(raw_line)
                if converted:
                    out_lines.append(converted)
                    if not converted.startswith("#"):
                        rule_count += 1

        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(f"# NAME: {src_path.name}.list\n")
            f.write(f"# TOTAL: {rule_count}\n")
            f.write(f"# REPO: https://github.com/{repo}\n")
            f.write(f"# UPDATED: {updated_str}\n")
            f.write("\n".join(out_lines) + "\n")

        return rule_count

    def build_whitelist_ips(
        self, src_path: Path, dst_path: Path, repo: str, updated_str: str
    ) -> int:
        ip_lines: List[str] = []
        ip_count = 0
        with open(src_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cidr = line.split()[0]
                ip_lines.append(f"IP-CIDR,{cidr},no-resolve")
                ip_count += 1

        with open(dst_path, "w", encoding="utf-8") as f:
            f.write("# NAME: whitelist-ips.list\n")
            f.write(f"# TOTAL: {ip_count}\n")
            f.write(f"# REPO: https://github.com/{repo}\n")
            f.write(f"# UPDATED: {updated_str}\n")
            f.write("\n".join(ip_lines) + "\n")

        return ip_count

    def build_direct_ips(
        self, sources: List[Path], dst_path: Path, repo: str, updated_str: str
    ) -> int:
        direct_ip_lines: List[str] = []
        seen_cidrs: Set[str] = set()

        for src in sources:
            if src.is_file():
                with open(src, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        cidr = line.split()[0].split("#")[0].strip()
                        if cidr and cidr not in seen_cidrs:
                            seen_cidrs.add(cidr)
                            direct_ip_lines.append(f"IP-CIDR,{cidr},no-resolve")

        with open(dst_path, "w", encoding="utf-8") as f:
            f.write("# NAME: direct-ips.list\n")
            f.write(f"# TOTAL: {len(direct_ip_lines)}\n")
            f.write(f"# REPO: https://github.com/{repo}\n")
            f.write(f"# UPDATED: {updated_str}\n")
            f.write("\n".join(direct_ip_lines) + "\n")

        return len(direct_ip_lines)

    def build_all_rulesets(
        self, repo: str, updated_str: Optional[str] = None
    ) -> Dict[str, int]:
        """Generate all .list files in SHADOWROCKET/rules/."""
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        if not updated_str:
            updated_str = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )

        counts: Dict[str, int] = {}

        # 1. Geosite domain lists (preserve existing list coverage)
        for p in sorted(self.geosite_data_dir.glob("*")):
            if p.is_file() and not p.name.startswith(".") and p.name != "android-push":
                out = self.rules_dir / f"{p.name}.list"
                counts[p.name] = self.build_ruleset_file(
                    p, out, repo=repo, updated_str=updated_str
                )

        # 2. GeoIP CIDR lists
        whitelist_ips_src = self.geoip_dir / "CUSTOM-WHITELIST.txt"
        if whitelist_ips_src.is_file():
            out = self.rules_dir / "whitelist-ips.list"
            counts["whitelist-ips"] = self.build_whitelist_ips(
                whitelist_ips_src, out, repo=repo, updated_str=updated_str
            )

        direct_sources = [
            self.geoip_dir / "CUSTOM-LIST-ADD.txt",
            self.geoip_dir / "CUSTOM-FIX-ADD.txt",
        ]
        out_direct = self.rules_dir / "direct-ips.list"
        counts["direct-ips"] = self.build_direct_ips(
            direct_sources, out_direct, repo=repo, updated_str=updated_str
        )

        return counts

    def emit_profile(
        self,
        profile_id: str,
        profile: ProfileConfig,
        output_dir: Path,
        repo: str,
        epoch: Optional[str] = None,
        updated_str: Optional[str] = None,
    ) -> None:
        """Emit Shadowrocket .CONF file matching exact legacy template specifications."""
        output_dir.mkdir(parents=True, exist_ok=True)
        key = profile_id.upper()
        branch = "main"
        raw_base = f"https://raw.githubusercontent.com/{repo}/{branch}/SHADOWROCKET"
        rules_base = f"{raw_base}/rules"

        if not epoch:
            now = datetime.datetime.now(datetime.timezone.utc)
            epoch_str = str(int(now.timestamp()))
            if not updated_str:
                updated_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            epoch_str = str(epoch)
            if not updated_str:
                # convert epoch to UTC format
                dt = datetime.datetime.fromtimestamp(
                    int(epoch), tz=datetime.timezone.utc
                )
                updated_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Format DnsHosts string
        hosts_lines = [
            f"{host} = {ip}" for host, ip in profile.dns_hosts.items()
        ]
        hosts_str = "\n".join(hosts_lines)

        profile_display = {
            "DEFAULT": "DEFAULT (Основной)",
            "WHITELIST": "WHITELIST (Белый список)",
            "BASIC": "BASIC (Базовый профиль)",
        }.get(key, profile.name)

        # Header template
        conf_header = f"""# @PinRouting for Shadowrocket
# Profile: {profile_display}
# LastUpdated: {epoch_str} ({updated_str})
# Repository: https://github.com/{repo}

[General]
# Системные сетевые вызовы (push-уведомления, системные сервисы iOS) обходят прокси
# bypass-system = true

# Отключение IPv6 для исключения утечек и задержек DNS
ipv6 = false
prefer-ipv6 = false

# Разрешение приватных IP адресов локальной сети
private-ip-answer = true

# Управление DNS: прямой системный DNS отключен для предотвращения перехвата и утечек
dns-direct-system = false
dns-fallback-system = false
dns-direct-fallback-proxy = true

# DNS серверы (100% аналог RemoteDns и DomesticDns из Happ и INCY):
# Основной удаленный DoH3/DoH: Quad9 (https://dns.quad9.net/dns-query, 9.9.9.9)
dns-server = https://dns.quad9.net/dns-query, 9.9.9.9

# Резервный отечественный DoH: Yandex (https://common.dot.dns.yandex.net/dns-query, 77.88.8.8)
fallback-dns-server = https://common.dot.dns.yandex.net/dns-query, 77.88.8.8, system

# Перехват стандартных DNS запросов (порт 53)
hijack-dns = :53

# Всегда возвращать реальный IP адрес (полный аналог FakeDNS: false)
always-real-ip = *

# Локальные сети и служебные домены в обход прокси через туннель
skip-proxy = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 127.0.0.1, localhost, *.local, captive.apple.com

# IP-диапазоны, исключенные из TUN-интерфейса
tun-excluded-routes = 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.0.0.0/24, 192.0.2.0/24, 192.88.99.0/24, 192.168.0.0/16, 198.51.100.0/24, 203.0.113.0/24, 224.0.0.0/4, 255.255.255.255/32, 239.255.255.250/32

icmp-auto-reply = false
always-reject-url-rewrite = false
udp-policy-not-supported-behaviour = REJECT

# Подключение пользовательских правил (не затираются при автообновлении)
include = EXTENDED.CONF

# URL автоматического обновления конфигурации
update-url = {raw_base}/{key}.CONF

[Host]
# Статические DNS-записи (100% аналог DnsHosts из Happ/INCY для гарантированного доступа к ФНС)
{hosts_str}
"""

        # Build [Rule] section dynamically from ProfileConfig
        rule_parts: List[str] = ["[Rule]"]

        # 1. Block rules
        if profile.block_sites:
            rule_parts.append("# --- Блокировка (BlockSites) ---")
            for s in profile.block_sites:
                cat = s.split(":", 1)[1] if ":" in s else s
                rule_parts.append(f"RULE-SET,{rules_base}/{cat}.list,REJECT")
            rule_parts.append("")

        # 2. Proxy rules (for DEFAULT and WHITELIST)
        if profile.proxy_sites:
            rule_parts.append(
                "# --- Проксируемые зарубежные сервисы (ProxySites) ---"
            )
            for s in profile.proxy_sites:
                cat = s.split(":", 1)[1] if ":" in s else s
                rule_parts.append(f"RULE-SET,{rules_base}/{cat}.list,PROXY")
            rule_parts.append("")

        # 3. Direct rules
        if profile.direct_sites:
            if key == "BASIC":
                rule_parts.append(
                    "# --- Прямое подключение (DirectSites: системные пуш-уведомления) ---"
                )
            else:
                rule_parts.append("# --- Прямое подключение (DirectSites) ---")
            for s in profile.direct_sites:
                cat = s.split(":", 1)[1] if ":" in s else s
                if cat not in ("android-push",):
                    rule_parts.append(f"RULE-SET,{rules_base}/{cat}.list,DIRECT")
            rule_parts.append("")

        # 4. Direct IP rules
        has_direct_ip = any(
            ip in ("geoip:direct", "geoip:ru", "geoip:custom-list-add")
            for ip in profile.direct_ip
        )
        has_whitelist_ip = any(
            ip in ("geoip:whitelist", "geoip:custom-whitelist")
            for ip in profile.direct_ip
        )

        if has_direct_ip:
            rule_parts.append("# --- Прямое подключение по IP (DirectIp) ---")
            rule_parts.append(
                f"RULE-SET,{rules_base}/direct-ips.list,DIRECT,no-resolve"
            )
            rule_parts.append("GEOIP,RU,DIRECT")
            rule_parts.append("GEOIP,BY,DIRECT")
            rule_parts.append("")
        elif has_whitelist_ip:
            rule_parts.append(
                "# --- Прямое подключение: IP белого списка РФ (DirectIp) ---"
            )
            rule_parts.append(
                f"RULE-SET,{rules_base}/whitelist-ips.list,DIRECT,no-resolve"
            )
            rule_parts.append("")

        # 5. Final fallback
        if profile.global_proxy == "true":
            if key == "BASIC":
                rule_parts.append(
                    "# --- Финальное правило (весь остальной трафик в VPN) ---"
                )
            else:
                rule_parts.append(
                    "# --- Финальное правило (аналог GlobalProxy: true — весь остальной зарубежный трафик в VPN) ---"
                )
            rule_parts.append("FINAL,PROXY\n")
        else:
            rule_parts.append(
                "# --- Финальное правило (GlobalProxy: false — весь остальной трафик напрямую) ---"
            )
            rule_parts.append("FINAL,DIRECT\n")

        conf_content = conf_header + "\n" + "\n".join(rule_parts)
        conf_path = output_dir / f"{key}.CONF"
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(conf_content)
