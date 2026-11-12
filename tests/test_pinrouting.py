"""Unit tests for logic that silently corrupts published configs when it breaks. Run: make test"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pinrouting.cli.check_iplists import check_built_list
from pinrouting.cli.lint import lint_profiles
from pinrouting.emitters.shadowrocket import ShadowrocketEmitter
from pinrouting.geosite import is_valid_domain, parse_rule, remove_domains
from pinrouting.models import ProfileConfig


class GeositeParseTest(unittest.TestCase):
    def test_parse_rule(self):
        self.assertEqual(parse_rule("example.com"), ("domain", "example.com"))
        self.assertEqual(parse_rule("full:Example.COM @ads # note"), ("full", "example.com"))
        self.assertEqual(parse_rule(r"regexp:^A\d+$"), ("regexp", r"^A\d+$"))
        self.assertIsNone(parse_rule("   # comment only"))
        self.assertIsNone(parse_rule("domain:"))

    def test_shadowrocket_strips_inline_comment_and_attrs(self):
        emit = ShadowrocketEmitter(Path(".")).convert_domain_rule
        self.assertEqual(emit("domain:foo.ru # bank"), "DOMAIN-SUFFIX,foo.ru")
        self.assertEqual(emit("full:foo.ru @ads"), "DOMAIN,foo.ru")
        self.assertEqual(emit("keyword:foo"), "DOMAIN-KEYWORD,foo")
        self.assertIsNone(emit("regexp:^foo$"))
        self.assertEqual(emit("# Section"), "# Section")

    def test_is_valid_domain_matches_v2fly(self):
        for ok in ("example.com", "a-b.example.com", "xn--p1ai", "3gppnetwork.org"):
            self.assertTrue(is_valid_domain(ok), ok)
        for bad in ("госуслуги.рф", "_dmarc.example.com", "example..com", "-a.com", "a-.com", "a" * 64 + ".com"):
            self.assertFalse(is_valid_domain(bad), bad)


class RemoveDomainsTest(unittest.TestCase):
    def test_removes_only_dead_domain_lines(self):
        source = (
            "# Banks\n"
            "domain:dead.example\n"
            "\n"
            "full:alive.example\n"
            "domain:dead.example.org\n"
            "keyword:dead\n"
            r"regexp:^dead\.example$" "\n"
            "full:dead.example @ads # dup with attr\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cat"
            path.write_text(source, encoding="utf-8")
            removed = remove_domains(path, {"dead.example"})
            self.assertEqual(removed, 2)
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "# Banks\n\nfull:alive.example\ndomain:dead.example.org\nkeyword:dead\n" r"regexp:^dead\.example$" "\n",
            )


@unittest.skipUnless(importlib.util.find_spec("dns"), "dnspython is not installed")
class DomainLivenessTest(unittest.TestCase):
    def test_suffix_rule_alive_when_subdomain_resolves(self):
        import dns.asyncresolver
        import dns.resolver
        from pinrouting.cli.check_dead import check_domain_liveness

        # Like xmpush.xiaomi.com: NXDOMAIN for the rule itself, a live name below it
        async def fake_resolve(self, name, rdtype):
            if name == "api.ent.example":
                return object()
            raise dns.resolver.NXDOMAIN

        def alive(domain: str, suffix: bool) -> bool:
            return asyncio.run(check_domain_liveness(domain, ["192.0.2.1"], retries=0, suffix=suffix))[0]

        with mock.patch.object(dns.asyncresolver.Resolver, "resolve", fake_resolve):
            self.assertTrue(alive("ent.example", suffix=True))
            self.assertFalse(alive("ent.example", suffix=False))
            self.assertFalse(alive("dead.example", suffix=True))


class LintProfilesTest(unittest.TestCase):
    def test_typos_in_profile_values_are_errors(self):
        profile = {
            "Name": "x",
            "FakeDNS": "ture",
            "RemoteDNSIP": "9.9.9",
            "DomainStrategy": "Bogus",
            "DirectSites": ["geosite:ok"],
            "ProxySites": ["domain:example.org"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ("profiles", "geosite/data", "geoip"):
                (root / d).mkdir(parents=True)
            (root / "geosite/data/ok").write_text("example.com\n", encoding="utf-8")
            (root / "geoip/config.json").write_text('{"input": []}', encoding="utf-8")
            (root / "profiles/X.json").write_text(json.dumps(profile), encoding="utf-8")
            errors = "\n".join(lint_profiles(root))
        for expected in ("FakeDNS", "RemoteDNSIP", "DomainStrategy", "domain:example.org"):
            self.assertIn(expected, errors)
        self.assertEqual(errors.count("\n"), 3, errors)  # nothing else is reported


class ShadowrocketProfileTest(unittest.TestCase):
    def test_ip_rule_without_equivalent_is_an_error(self):
        cfg = ProfileConfig.from_dict({"Name": "x", "DirectIp": ["geoip:private"], "BlockIp": ["203.0.113.0/24"]})
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "203.0.113.0/24"):
            ShadowrocketEmitter(Path(tmp)).emit_profile("X", cfg, Path(tmp), repo="o/r", epoch="0", updated_str="")


class IpListGateTest(unittest.TestCase):
    def test_built_list_too_big_or_foreign(self):
        self.assertEqual(check_built_list("whitelist", "77.88.8.0/24\n2a02:6b8::/32\n"), [])
        errors = check_built_list("whitelist", "77.88.8.0/24\n0.0.0.0/0\n")
        self.assertEqual(len(errors), 2)  # over the address limit, and 8.8.8.8 goes DIRECT
        self.assertEqual(len(check_built_list("direct", "8.8.8.0/24\n")), 1)


class ProfileConfigTest(unittest.TestCase):
    def test_unknown_key_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "ProxySite"):
            ProfileConfig.from_dict({"Name": "x", "ProxySite": ["geosite:youtube"]})

    def test_known_keys_load(self):
        cfg = ProfileConfig.from_dict({"Name": "x", "ProxySites": ["geosite:youtube"], "GlobalProxy": True})
        self.assertEqual(cfg.proxy_sites, ["geosite:youtube"])
        self.assertEqual(cfg.global_proxy, "true")


if __name__ == "__main__":
    unittest.main()
