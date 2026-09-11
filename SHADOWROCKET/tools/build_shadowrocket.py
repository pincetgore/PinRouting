#!/usr/bin/env python3
"""
Shadowrocket Configuration and Rules Generator for PinRouting.

Translates geosite/data and geoip lists into Shadowrocket-compatible .list
rulesets and builds configuration profiles (DEFAULT.CONF, WHITELIST.CONF,
BASIC.CONF, EXTENDED.CONF) with 100% parameter parity to HAPP and INCY.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

REPO_DEFAULT = "pincetgore/PinRouting"
BRANCH_DEFAULT = "main"

def parse_args():
    parser = argparse.ArgumentParser(description="Build Shadowrocket configurations and rulesets.")
    parser.add_argument("--repo", default=REPO_DEFAULT, help="GitHub repository (owner/name)")
    parser.add_argument("--branch", default=BRANCH_DEFAULT, help="Git branch for raw URLs")
    parser.add_argument("--geosite-dir", default=os.path.join(REPO_ROOT, "geosite", "data"), help="Path to geosite data directory")
    parser.add_argument("--output-dir", default=os.path.join(REPO_ROOT, "SHADOWROCKET"), help="Path to output directory")
    parser.add_argument("--epoch", default=None, help="Epoch timestamp for LastUpdated")
    return parser.parse_args()

def convert_geosite_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    if line.startswith("#"):
        return line
    
    # Strip inline comment if present
    comment = ""
    if "#" in line:
        parts = line.split("#", 1)
        line = parts[0].strip()
        comment = " # " + parts[1].strip()

    if not line:
        return ""

    if ":" in line:
        rule_type, val = line.split(":", 1)
        rule_type = rule_type.strip().lower()
        val = val.strip().split()[0].lower() # take domain without attributes
        if rule_type == "full":
            return f"DOMAIN,{val}{comment}"
        elif rule_type == "keyword":
            return f"DOMAIN-KEYWORD,{val}{comment}"
        elif rule_type == "regexp":
            return f"URL-REGEX,{val}{comment}"
        else:
            return f"DOMAIN-SUFFIX,{val}{comment}"
    else:
        val = line.split()[0].lower()
        return f"DOMAIN-SUFFIX,{val}{comment}"

def build_rulesets(geosite_dir: str, rules_dir: str, repo: str, updated_str: str):
    os.makedirs(rules_dir, exist_ok=True)
    categories = sorted(os.listdir(geosite_dir))

    for cat in categories:
        src_path = os.path.join(geosite_dir, cat)
        if not os.path.isfile(src_path) or cat.startswith(".") or cat == "android-push":
            continue

        out_lines = []
        rule_count = 0
        with open(src_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                converted = convert_geosite_line(raw_line)
                if converted:
                    out_lines.append(converted)
                    if not converted.startswith("#"):
                        rule_count += 1

        dst_path = os.path.join(rules_dir, f"{cat}.list")
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(f"# NAME: {cat}.list\n")
            f.write(f"# TOTAL: {rule_count}\n")
            f.write(f"# REPO: https://github.com/{repo}\n")
            f.write(f"# UPDATED: {updated_str}\n")
            f.write("\n".join(out_lines) + "\n")
        print(f"Generated {dst_path} ({rule_count} rules)")

    # Generate whitelist-ips.list from geoip/CUSTOM-WHITELIST.txt
    custom_whitelist_path = os.path.join(REPO_ROOT, "geoip", "CUSTOM-WHITELIST.txt")
    if os.path.isfile(custom_whitelist_path):
        ip_lines = []
        ip_count = 0
        with open(custom_whitelist_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cidr = line.split()[0]
                ip_lines.append(f"IP-CIDR,{cidr},no-resolve")
                ip_count += 1

        dst_path = os.path.join(rules_dir, "whitelist-ips.list")
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write("# NAME: whitelist-ips.list\n")
            f.write(f"# TOTAL: {ip_count}\n")
            f.write(f"# REPO: https://github.com/{repo}\n")
            f.write(f"# UPDATED: {updated_str}\n")
            f.write("\n".join(ip_lines) + "\n")
        print(f"Generated {dst_path} ({ip_count} IP CIDR rules)")

def get_general_and_host_section(profile_name: str, filename: str, repo: str, branch: str, epoch: str, updated_str: str) -> str:
    raw_base = f"https://raw.githubusercontent.com/{repo}/{branch}/SHADOWROCKET"
    return f"""# @PinRouting for Shadowrocket
# Profile: {profile_name}
# LastUpdated: {epoch} ({updated_str})
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
# Основной удаленный DoH: Quad9 (https://dns.quad9.net/dns-query, 9.9.9.9)
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
update-url = {raw_base}/{filename}

[Host]
# Статические DNS-записи (100% аналог DnsHosts из Happ/INCY для гарантированного доступа к ФНС)
lkfl2.nalog.ru = 213.24.64.175
lknpd.nalog.ru = 213.24.64.181
"""

def build_default_conf(out_path: str, repo: str, branch: str, epoch: str, updated_str: str):
    rules_base = f"https://raw.githubusercontent.com/{repo}/{branch}/SHADOWROCKET/rules"
    content = get_general_and_host_section("DEFAULT (Основной)", "DEFAULT.CONF", repo, branch, epoch, updated_str)
    content += f"""
[Rule]
# --- Блокировка (BlockSites) ---
RULE-SET,{rules_base}/win-spy.list,REJECT
RULE-SET,{rules_base}/torrent.list,REJECT
RULE-SET,{rules_base}/category-ads.list,REJECT

# --- Проксируемые зарубежные сервисы (ProxySites) ---
RULE-SET,{rules_base}/category-geoblock-ru.list,PROXY
RULE-SET,{rules_base}/github.list,PROXY
RULE-SET,{rules_base}/twitch-ads.list,REJECT
RULE-SET,{rules_base}/youtube.list,PROXY
RULE-SET,{rules_base}/telegram.list,PROXY

# --- Прямое подключение (DirectSites) ---
RULE-SET,{rules_base}/private.list,DIRECT
RULE-SET,{rules_base}/apple-push.list,DIRECT
RULE-SET,{rules_base}/category-ru.list,DIRECT
RULE-SET,{rules_base}/whitelist.list,DIRECT
RULE-SET,{rules_base}/domains-geo-detect.list,DIRECT
RULE-SET,{rules_base}/domains-ipchecker.list,DIRECT
RULE-SET,{rules_base}/microsoft.list,DIRECT
RULE-SET,{rules_base}/steam.list,DIRECT
RULE-SET,{rules_base}/twitch.list,DIRECT
RULE-SET,{rules_base}/pinterest.list,DIRECT

# --- Прямое подключение по IP (DirectIp) ---
GEOIP,RU,DIRECT
GEOIP,BY,DIRECT

# --- Финальное правило (аналог GlobalProxy: true — весь остальной зарубежный трафик в VPN) ---
FINAL,PROXY
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated {out_path}")

def build_whitelist_conf(out_path: str, repo: str, branch: str, epoch: str, updated_str: str):
    rules_base = f"https://raw.githubusercontent.com/{repo}/{branch}/SHADOWROCKET/rules"
    content = get_general_and_host_section("WHITELIST (Белый список)", "WHITELIST.CONF", repo, branch, epoch, updated_str)
    content += f"""
[Rule]
# --- Блокировка (BlockSites) ---
RULE-SET,{rules_base}/win-spy.list,REJECT
RULE-SET,{rules_base}/torrent.list,REJECT
RULE-SET,{rules_base}/category-ads.list,REJECT

# --- Прямое подключение: только белые списки (DirectSites) ---
RULE-SET,{rules_base}/private.list,DIRECT
RULE-SET,{rules_base}/apple-push.list,DIRECT
RULE-SET,{rules_base}/whitelist.list,DIRECT

# --- Прямое подключение: IP белого списка РФ (DirectIp) ---
RULE-SET,{rules_base}/whitelist-ips.list,DIRECT,no-resolve

# --- Проксируемые сервисы (ProxySites) ---
RULE-SET,{rules_base}/category-geoblock-ru.list,PROXY

# --- Финальное правило (весь остальной трафик в VPN) ---
FINAL,PROXY
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated {out_path}")

def build_basic_conf(out_path: str, repo: str, branch: str, epoch: str, updated_str: str):
    rules_base = f"https://raw.githubusercontent.com/{repo}/{branch}/SHADOWROCKET/rules"
    content = get_general_and_host_section("BASIC (Базовый профиль)", "BASIC.CONF", repo, branch, epoch, updated_str)
    content += f"""
[Rule]
# --- Прямое подключение (DirectSites: системные пуш-уведомления) ---
RULE-SET,{rules_base}/apple-push.list,DIRECT

# --- Финальное правило (весь остальной трафик в VPN) ---
FINAL,PROXY
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated {out_path}")

def build_extended_conf(out_path: str):
    content = """# Пользовательские правила маршрутизации Shadowrocket
# Этот файл подключается в основные конфигурации через 'include = EXTENDED.CONF'
# Добавленные сюда правила имеют приоритет и НЕ затираются при автообновлении подписки.

[Rule]
# Примеры добавления собственных правил:
# DOMAIN-SUFFIX,example.com,DIRECT
# DOMAIN,sub.example.com,PROXY
# DOMAIN-KEYWORD,mycustomservice,PROXY
# IP-CIDR,198.51.100.0/24,PROXY,no-resolve
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated {out_path}")

def main():
    args = parse_args()

    epoch = args.epoch
    if not epoch:
        happ_default = os.path.join(REPO_ROOT, "HAPP", "DEFAULT.JSON")
        if os.path.isfile(happ_default):
            with open(happ_default, "r", encoding="utf-8") as f:
                data = json.load(f)
                epoch = str(data.get("LastUpdated", int(time.time())))
        else:
            epoch = str(int(time.time()))

    updated_dt = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    updated_str = updated_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    rules_dir = os.path.join(args.output_dir, "rules")
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(rules_dir, exist_ok=True)

    print(f"Building Shadowrocket rulesets in {rules_dir}...")
    build_rulesets(args.geosite_dir, rules_dir, args.repo, updated_str)

    print("Building Shadowrocket configuration profiles...")
    build_default_conf(os.path.join(args.output_dir, "DEFAULT.CONF"), args.repo, args.branch, epoch, updated_str)
    build_whitelist_conf(os.path.join(args.output_dir, "WHITELIST.CONF"), args.repo, args.branch, epoch, updated_str)
    build_basic_conf(os.path.join(args.output_dir, "BASIC.CONF"), args.repo, args.branch, epoch, updated_str)
    build_extended_conf(os.path.join(args.output_dir, "EXTENDED.CONF"))

    print("Shadowrocket build completed successfully!")

if __name__ == "__main__":
    main()
