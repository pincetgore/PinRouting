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
GEOSITE_DATA_DIR = REPO_ROOT / "geosite" / "data"
HAPP_DEFAULT_JSON = REPO_ROOT / "HAPP" / "DEFAULT.JSON"
INCY_DEFAULT_JSON = REPO_ROOT / "INCY" / "DEFAULT.JSON"
SHADOWROCKET_DEFAULT_CONF = REPO_ROOT / "SHADOWROCKET" / "DEFAULT.CONF"


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
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                content = line.split("#", 1)[0].strip()
                parts = content.split("@")[0].strip()
                if not parts:
                    continue

                if ":" in parts:
                    rtype, val = parts.split(":", 1)
                    rtype = rtype.strip().lower()
                    val = val.strip().lower()
                else:
                    rtype = "domain"
                    val = parts.lower()

                if rtype == "domain":
                    self.domain_suffixes.add(val)
                elif rtype == "full":
                    self.full_domains.add(val)
                elif rtype == "keyword":
                    self.keywords.append(val)
                elif rtype == "regexp":
                    try:
                        self.regexps.append(re.compile(val, re.IGNORECASE))
                    except re.error:
                        pass

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


class RoutingTestSuite:
    """Loads configs and tests domain routing decisions."""

    def __init__(self):
        self.matchers: dict[str, GeositeMatcher] = {}
        for item in GEOSITE_DATA_DIR.iterdir():
            if item.is_file() and not item.name.startswith("."):
                self.matchers[item.name] = GeositeMatcher(item.name, item)

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
                url = parts[1]
                action = parts[2].upper()
                list_name = Path(url).name.removesuffix(".list")
                matcher = self.matchers.get(list_name)
                if matcher and matcher.matches(domain):
                    return action

            elif rtype == "DOMAIN":
                if domain.lower() == parts[1].lower():
                    return parts[2].upper()
            elif rtype == "DOMAIN-SUFFIX":
                suffix = parts[1].lower().strip(".")
                if domain.lower() == suffix or domain.lower().endswith("." + suffix):
                    return parts[2].upper()
            elif rtype == "DOMAIN-KEYWORD":
                if parts[1].lower() in domain.lower():
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
            ("nalog.gov.ru", "DIRECT", "Tax service"),
            ("cbr.ru", "DIRECT", "Central Bank of Russia"),
            ("nspk.ru", "DIRECT", "NSPK Mir"),
            # Push notifications and VoWiFi -> strictly DIRECT
            ("3gppnetwork.org", "DIRECT", "VoWiFi root"),
            ("epdg.epc.mnc002.mcc250.pub.3gppnetwork.org", "DIRECT", "Megafon VoWiFi ePDG"),
            ("gateway.icloud.com", "DIRECT", "Apple push/iCloud"),
            # Direct media and gaming -> DIRECT
            ("steamcommunity.com", "DIRECT", "Steam"),
            ("steampowered.com", "DIRECT", "Steam Store"),
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

        print("=" * 80)
        print("  PinRouting Routing Simulation & Regression Test Suite")
        print("=" * 80)

        failed = 0
        total = 0

        print("\n--- Universal Profiles (HAPP, INCY, Shadowrocket) ---")
        for domain, expected, description in universal_cases:
            total += 1
            happ_res = self._resolve_json(HAPP_DEFAULT_JSON, domain)
            sr_res = self._resolve_shadowrocket(SHADOWROCKET_DEFAULT_CONF, domain)
            sr_normalized = "BLOCK" if sr_res in ("REJECT", "REJECT-DROP") else sr_res

            happ_ok = happ_res == expected
            sr_ok = sr_normalized == expected

            if happ_ok and sr_ok:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
                failed += 1

            details = f"HAPP: {happ_res}, SR: {sr_res}" if not (happ_ok and sr_ok) else happ_res
            print(f" {status} | {domain:<35} | exp: {expected:<6} | {details:<16} | {description}")

        print("\n--- Android-specific Services (HAPP & INCY) ---")
        for domain, expected, description in android_cases:
            total += 1
            happ_res = self._resolve_json(HAPP_DEFAULT_JSON, domain)
            incy_res = self._resolve_json(INCY_DEFAULT_JSON, domain)

            happ_ok = happ_res == expected
            incy_ok = incy_res == expected

            if happ_ok and incy_ok:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
                failed += 1

            details = f"HAPP: {happ_res}, INCY: {incy_res}" if not (happ_ok and incy_ok) else happ_res
            print(f" {status} | {domain:<35} | exp: {expected:<6} | {details:<16} | {description}")

        print("=" * 80)
        print(f"Summary: {total - failed}/{total} passed, {failed} failed")
        print("=" * 80)

        return 1 if failed > 0 else 0


def main():
    suite = RoutingTestSuite()
    sys.exit(suite.run_tests())


if __name__ == "__main__":
    main()
