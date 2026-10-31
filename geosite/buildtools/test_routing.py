#!/usr/bin/env python3
"""Routing simulation and regression test suite for PinRouting.

Simulates routing resolution across HAPP, INCY, and Shadowrocket configuration
profiles against expected routing destinations (DIRECT, PROXY, BLOCK/REJECT).

Usage:
  python3 test_routing.py
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from pinrouting.geosite import parse_rule

GEOSITE_DATA_DIR = REPO_ROOT / "geosite" / "data"
SHADOWROCKET_DIR = REPO_ROOT / "SHADOWROCKET"
SHADOWROCKET_RULES_DIR = SHADOWROCKET_DIR / "rules"
# jsDelivr serves @<commit> immutably; @release stayed stale for hours even after a purge
PINNED_GEODATA_URL = re.compile(r"https://cdn\.jsdelivr\.net/gh/[^/@]+/[^/@]+@[0-9a-f]{40}/geo(ip|site)\.dat")


class GeositeMatcher:
    """Matches domains against geosite rule definitions."""

    def __init__(self, category: str, rules_path: Path):
        self.category = category
        self.domain_suffixes: set[str] = set()
        self.full_domains: set[str] = set()
        self.keywords: list[str] = []
        self.regexps: list[re.Pattern[str]] = []
        self._load(rules_path)

    def _load(self, filepath: Path) -> None:
        if not filepath.is_file():
            return
        with open(filepath, "r", encoding="utf-8") as f:
            for raw_line in f:
                rule = parse_rule(raw_line)
                if rule is None:
                    continue
                rtype, val = rule
                if rtype == "domain":
                    self.domain_suffixes.add(val)
                elif rtype == "full":
                    self.full_domains.add(val)
                elif rtype == "keyword":
                    self.keywords.append(val)
                elif rtype == "regexp":
                    self.regexps.append(re.compile(val, re.IGNORECASE))

    def matches(self, domain: str) -> bool:
        domain = domain.lower().strip(".")
        if domain in self.full_domains:
            return True

        curr = domain
        while curr:
            if curr in self.domain_suffixes:
                return True
            if "." in curr:
                curr = curr.split(".", 1)[1]
            else:
                break

        for kw in self.keywords:
            if kw in domain:
                return True

        for rgx in self.regexps:
            if rgx.search(domain):
                return True

        return False


def shadowrocket_rule_matches(rtype: str, value: str, domain: str) -> bool:
    """Matches a single Shadowrocket domain rule (DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD)."""
    domain = domain.lower()
    value = value.lower().strip(".")
    if rtype == "DOMAIN":
        return domain == value
    if rtype == "DOMAIN-SUFFIX":
        return domain == value or domain.endswith("." + value)
    if rtype == "DOMAIN-KEYWORD":
        return value in domain
    return False


class ShadowrocketListMatcher:
    """Matches domains against a generated SHADOWROCKET/rules/*.list file (what the client really loads)."""

    def __init__(self, list_path: Path):
        self.rules: list[tuple[str, str]] = []
        with open(list_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    self.rules.append((parts[0].upper(), parts[1]))

    def matches(self, domain: str) -> bool:
        return any(shadowrocket_rule_matches(rtype, value, domain) for rtype, value in self.rules)


class RoutingTestSuite:
    """Loads configs and tests domain routing decisions."""

    def __init__(self):
        self.matchers: dict[str, GeositeMatcher] = {}
        for item in GEOSITE_DATA_DIR.iterdir():
            if item.is_file() and not item.name.startswith("."):
                self.matchers[item.name] = GeositeMatcher(item.name, item)
        self.sr_matchers: dict[str, ShadowrocketListMatcher] = {}

    def _sr_list(self, list_name: str) -> ShadowrocketListMatcher:
        if list_name not in self.sr_matchers:
            path = SHADOWROCKET_RULES_DIR / f"{list_name}.list"
            if not path.is_file():
                raise FileNotFoundError(f"Shadowrocket RULE-SET references missing list: {path}")
            self.sr_matchers[list_name] = ShadowrocketListMatcher(path)
        return self.sr_matchers[list_name]

    def _resolve_json(self, config_path: Path, domain: str) -> str:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # BlockSites
        for entry in cfg.get("BlockSites", []):
            cat = entry.removeprefix("geosite:")
            matcher = self.matchers.get(cat)
            if matcher and matcher.matches(domain):
                return "BLOCK"

        # ProxySites
        for entry in cfg.get("ProxySites", []):
            cat = entry.removeprefix("geosite:")
            matcher = self.matchers.get(cat)
            if matcher and matcher.matches(domain):
                return "PROXY"

        # DirectSites
        for entry in cfg.get("DirectSites", []):
            cat = entry.removeprefix("geosite:")
            matcher = self.matchers.get(cat)
            if matcher and matcher.matches(domain):
                return "DIRECT"

        if cfg.get("GlobalProxy") in (True, "true"):
            return "PROXY"
        return "DIRECT"

    def _resolve_shadowrocket(self, conf_path: Path, domain: str) -> str:
        with open(conf_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        in_rule = False
        for raw in lines:
            line = raw.strip()
            if line == "[Rule]":
                in_rule = True
                continue
            if not in_rule or not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(",")]
            rtype = parts[0].upper()

            if rtype == "RULE-SET":
                list_name = Path(parts[1]).name.removesuffix(".list")
                if self._sr_list(list_name).matches(domain):
                    return parts[2].upper()
            elif rtype in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"):
                if shadowrocket_rule_matches(rtype, parts[1], domain):
                    return parts[2].upper()
            elif rtype == "FINAL":
                return parts[1].upper()

        return "DIRECT"

    def run_tests(self) -> int:
        universal_cases = [
            # Russian public services and banks -> strictly DIRECT
            ("gosuslugi.ru", "DIRECT", "State services"),
            ("gu-st.ru", "DIRECT", "State services CDN"),
            ("sberbank.ru", "DIRECT", "Sberbank"),
            ("tbank.ru", "DIRECT", "T-Bank"),
            ("servicecdn.ru", "DIRECT", "Alfa-Bank CDN"),
            ("nalog.gov.ru", "DIRECT", "Tax service"),
            ("cbr.ru", "DIRECT", "Central Bank of Russia"),
            ("nspk.ru", "DIRECT", "NSPK Mir"),
            # Push notifications and VoWiFi -> strictly DIRECT
            ("3gppnetwork.org", "DIRECT", "VoWiFi root"),
            ("epdg.epc.mnc002.mcc250.pub.3gppnetwork.org", "DIRECT", "Megafon VoWiFi ePDG"),
            ("gateway.icloud.com", "DIRECT", "Apple push/iCloud"),
            # Mobile App Store & Google Play direct updates -> DIRECT
            ("updates.cdn-apple.com", "DIRECT", "Apple App Store / iOS updates CDN"),
            ("appldnld.apple.com", "DIRECT", "Apple software download CDN"),
            ("play.google.com", "DIRECT", "Google Play Store"),
            ("play.googleapis.com", "DIRECT", "Google Play API & APKs"),
            ("ggpht.com", "PROXY", "YouTube / Google images"),
            # Direct media and gaming -> DIRECT
            ("twitch.tv", "DIRECT", "Twitch"),
            ("pinterest.com", "DIRECT", "Pinterest"),
            # Social networks and foreign services -> PROXY
            ("instagram.com", "PROXY", "Instagram web"),
            ("cdninstagram.com", "PROXY", "Instagram media CDN"),
            ("threads.net", "PROXY", "Threads"),
            ("x.com", "PROXY", "X"),
            ("twitter.com", "PROXY", "Twitter"),
            ("twimg.com", "PROXY", "Twitter image CDN"),
            ("t.co", "PROXY", "Twitter shortlink"),
            ("youtube.com", "PROXY", "YouTube web"),
            ("googlevideo.com", "PROXY", "YouTube video stream"),
            ("t.me", "PROXY", "Telegram shortlink"),
            ("telegram.org", "PROXY", "Telegram portal"),
            ("github.com", "PROXY", "GitHub web"),
            ("raw.githubusercontent.com", "PROXY", "GitHub raw user content"),
            # AI & Geoblocked services -> PROXY
            ("gemini.google.com", "PROXY", "Google Gemini AI"),
            ("gemini.gstatic.com", "PROXY", "Google Gemini static assets"),
            ("console.cloud.google.com", "PROXY", "Google Cloud console (google.com is DIRECT)"),
            ("www.google.com", "DIRECT", "Google search via geosite:whitelist"),
            ("copilot.microsoft.com", "PROXY", "Microsoft Copilot AI"),
            ("chatgpt.com", "PROXY", "OpenAI ChatGPT"),
            ("oaistatic.com", "PROXY", "OpenAI static assets"),
            ("claude.ai", "PROXY", "Anthropic Claude"),
            ("anthropic.com", "PROXY", "Anthropic API"),
            # Blocked trackers and ads -> BLOCK
            ("tracker.opentrackr.com", "BLOCK", "Torrent tracker"),
            ("adservice.google.com", "BLOCK", "Google adservice"),
            # Unlisted foreign domain -> fallback to PROXY
            ("random-foreign-service.org", "PROXY", "Generic foreign site"),
        ]

        android_cases = [
            ("connectivitycheck.gstatic.com", "DIRECT", "Android captive portal check"),
            ("mtalk.google.com", "DIRECT", "Google FCM push"),
            ("push.hicloud.com", "DIRECT", "Huawei Push root"),
            ("pushtrs.push.hicloud.com", "DIRECT", "Huawei Push delivery node"),
            ("token-drcn.push.dbankcloud.com", "DIRECT", "Huawei HMS push token"),
        ]

        whitelist_cases = [
            ("gosuslugi.ru", "DIRECT", "State services"),
            ("sberbank.ru", "DIRECT", "Sberbank"),
            ("gateway.icloud.com", "DIRECT", "Apple push/iCloud"),
            ("youtube.com", "PROXY", "YouTube web"),
            ("ggpht.com", "PROXY", "YouTube / Google images"),
            ("wide-youtube.l.google.com", "PROXY", "YouTube via google.com subdomain"),
            ("pay.google.com", "PROXY", "Google Pay via google.com subdomain"),
            ("instagram.com", "PROXY", "Instagram web"),
            ("chatgpt.com", "PROXY", "OpenAI ChatGPT"),
            ("adservice.google.com", "BLOCK", "Google adservice"),
            ("random-foreign-service.org", "PROXY", "Generic foreign site"),
        ]

        basic_cases = [
            ("gateway.icloud.com", "DIRECT", "Apple push/iCloud"),
            ("gosuslugi.ru", "PROXY", "No site rules: everything else via VPN"),
            ("youtube.com", "PROXY", "YouTube web"),
        ]

        basic_android_cases = [
            ("mtalk.google.com", "DIRECT", "Google FCM push"),
        ]

        print("=" * 80)
        print("  PinRouting Routing Simulation & Regression Test Suite")
        print("=" * 80)

        failed = 0
        total = 0

        def happ(profile: str):
            return "HAPP", lambda d: self._resolve_json(REPO_ROOT / "HAPP" / f"{profile}.JSON", d)

        def incy(profile: str):
            return "INCY", lambda d: self._resolve_json(REPO_ROOT / "INCY" / f"{profile}.JSON", d)

        def shadowrocket(profile: str):
            def resolve(d: str) -> str:
                res = self._resolve_shadowrocket(SHADOWROCKET_DIR / f"{profile}.CONF", d)
                return "BLOCK" if res in ("REJECT", "REJECT-DROP") else res
            return "SR", resolve

        suites = [
            ("DEFAULT (HAPP, INCY, Shadowrocket)", universal_cases, [happ("DEFAULT"), incy("DEFAULT"), shadowrocket("DEFAULT")]),
            ("DEFAULT Android-specific (HAPP & INCY)", android_cases, [happ("DEFAULT"), incy("DEFAULT")]),
            ("WHITELIST (HAPP, INCY, Shadowrocket)", whitelist_cases, [happ("WHITELIST"), incy("WHITELIST"), shadowrocket("WHITELIST")]),
            ("BASIC (HAPP, INCY, Shadowrocket)", basic_cases, [happ("BASIC"), incy("BASIC"), shadowrocket("BASIC")]),
            ("BASIC Android-specific (HAPP & INCY)", basic_android_cases, [happ("BASIC"), incy("BASIC")]),
        ]
        for title, cases, clients in suites:
            print(f"\n--- {title} ---")
            for domain, expected, description in cases:
                total += 1
                results = [(label, resolve(domain)) for label, resolve in clients]
                ok = all(res == expected for _, res in results)
                if not ok:
                    failed += 1
                details = expected if ok else ", ".join(f"{label}: {res}" for label, res in results)
                print(f" {'✅ PASS' if ok else '❌ FAIL'} | {domain:<35} | exp: {expected:<6} | {details:<16} | {description}")

        # With no-resolve Shadowrocket skips IP rules for domain requests, unlike Happ/INCY (IPIfNonMatch)
        print("\n--- Shadowrocket IP rule sets resolve domains ---")
        for path in sorted(SHADOWROCKET_RULES_DIR.glob("*-ips.list")) + sorted(SHADOWROCKET_DIR.glob("*.CONF")):
            total += 1
            bad = [ln for ln in path.read_text(encoding="utf-8").splitlines()
                   if "no-resolve" in ln and not ln.startswith("#") and (path.suffix == ".list" or "-ips.list" in ln)]
            if bad:
                failed += 1
            print(f" {'❌ FAIL' if bad else '✅ PASS'} | {path.name:<35} | {bad[0] if bad else 'no no-resolve'}")

        print("\n--- Happ/INCY geodata URLs pinned to a release commit ---")
        for path in sorted((REPO_ROOT / "HAPP").glob("*.JSON")) + sorted((REPO_ROOT / "INCY").glob("*.JSON")):
            total += 1
            cfg = json.loads(path.read_text(encoding="utf-8"))
            bad = [u for u in (cfg["Geoipurl"], cfg["Geositeurl"]) if not PINNED_GEODATA_URL.fullmatch(u)]
            if bad:
                failed += 1
            print(f" {'❌ FAIL' if bad else '✅ PASS'} | {path.parent.name + '/' + path.name:<35} | {bad[0] if bad else 'pinned'}")

        print("=" * 80)
        print(f"Summary: {total - failed}/{total} passed, {failed} failed")
        print("=" * 80)

        return 1 if failed > 0 else 0


def main():
    suite = RoutingTestSuite()
    sys.exit(suite.run_tests())


if __name__ == "__main__":
    main()
