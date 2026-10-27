"""Unit tests for logic that silently corrupts published configs when it breaks. Run: make test"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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
