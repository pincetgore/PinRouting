"""Unit tests for logic that silently corrupts published configs when it breaks. Run: make test"""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pinrouting.cli.build import build_all
from pinrouting.cli.check_iplists import (
    MIN_CIDRS,
    check_built_list,
    check_download,
    check_downloads,
    check_whitelist_geo,
)
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


def load_buildtool(name: str):
    """Imports a standalone script from geosite/buildtools."""
    path = Path(__file__).resolve().parent.parent / "geosite" / "buildtools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LintRulesTest(unittest.TestCase):
    def test_full_rule_repeating_a_domain_rule_is_an_error(self):
        lint_geosite_file = load_buildtool("lint_rules").lint_geosite_file
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            path = Path(tmp) / "cat"
            path.write_text("full:x.example\ndomain:x.example\n", encoding="utf-8")
            self.assertEqual(lint_geosite_file(path), (1, 0))
            path.write_text("full:a.x.example\ndomain:x.example\nfull:y.example\n", encoding="utf-8")
            self.assertEqual(lint_geosite_file(path), (0, 1))

    def test_geoip_line_is_read_like_the_build_reads_it(self):
        # lint must reject what the Shadowrocket emitter cannot parse, and accept inline comments
        lint_geoip_file = load_buildtool("lint_rules").lint_geoip_file
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            path = Path(tmp) / "list.txt"
            path.write_text("10.0.0.0/24 # office\n10.0.2.0/24 junk\n", encoding="utf-8")
            self.assertEqual(lint_geoip_file(path), (1, 0))


class DeduplicateTest(unittest.TestCase):
    def test_ip_in_direct(self):
        dedup = load_buildtool("deduplicate")
        nets, starts = dedup.parse_cidrs_from_text("# c\n10.0.1.0/24\n10.0.0.0/24\n10.0.0.128/25\n2a02:6b8::/32\nbad\n")
        self.assertEqual([str(n) for n in nets], ["10.0.0.0/23"])
        for ip, inside in (("10.0.0.0", True), ("10.0.1.255", True), ("10.0.2.0", False), ("9.255.255.255", False), ("x", False)):
            self.assertEqual(dedup.ip_in_direct(ip, nets, starts), inside, ip)

    def test_ipv6_only_answer_is_not_nxdomain(self):
        # check-host.net shapes: NXDOMAIN is A=[] and AAAA=[] with TTL null; IPv6-only has AAAA but no A
        dedup = load_buildtool("deduplicate")
        nets, starts = dedup.parse_cidrs_from_text("77.88.8.0/24\n")
        direct = [{"A": ["77.88.8.8"], "AAAA": [], "TTL": 60}]
        ipv6_only = [{"A": [], "AAAA": ["2a00:1450:4001:c0f::71"], "TTL": 110}]
        nxdomain = [{"A": [], "AAAA": [], "TTL": None}]

        def check(foreign):
            nodes = {n: direct for n in dedup.RU_NODES} | {g[0]: foreign for g in dedup.FOREIGN_NODES}
            api = lambda url: {"request_id": "r"} if "/check-dns?" in url else nodes
            with mock.patch.object(dedup, "curl_json", api), mock.patch.object(dedup.time, "sleep"):
                return dedup.check_one_domain(1, "domain", "x.example", nets, starts)[3]

        self.assertTrue(check(direct))
        self.assertTrue(check(nxdomain))  # direct where it resolves, gone elsewhere: still a candidate
        self.assertFalse(check(ipv6_only))  # abroad it lives on IPv6 we cannot place: keep it

    def test_inline_comment_keeps_the_cidr(self):
        nets, _ = load_buildtool("deduplicate").parse_cidrs_from_text("10.0.0.0/24 # office # floor 2\n")
        self.assertEqual([str(n) for n in nets], ["10.0.0.0/24"])


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

    def test_categories_must_exist_in_the_repo(self):
        geoip_config = {"input": [
            {"type": "text", "action": "remove", "args": {"name": "gone"}},
            {"type": "private", "action": "add"},
            {"type": "text", "action": "add", "args": {"name": "RU"}},
            {"type": "maxmindMMDB", "action": "add", "args": {"wantedList": ["BY"]}},
        ]}
        profile = {
            "Name": "x",
            "ProxySites": ["geosite:ok", "geosite:missing", "geosite:.DS_Store"],
            "DirectIp": ["geoip:ru", "geoip:by", "geoip:private", "geoip:gone", "10.0.0.0/8"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ("profiles", "geosite/data", "geoip"):
                (root / d).mkdir(parents=True)
            (root / "geosite/data/ok").write_text("example.com\n", encoding="utf-8")
            (root / "geosite/data/.DS_Store").write_text("", encoding="utf-8")  # Finder litter is not a category
            (root / "geoip/config.json").write_text(json.dumps(geoip_config), encoding="utf-8")
            (root / "profiles/X.json").write_text(json.dumps(profile), encoding="utf-8")
            errors = lint_profiles(root)
        self.assertEqual(len(errors), 3, errors)
        self.assertIn("'missing'", errors[0])
        self.assertIn("'.DS_Store'", errors[1])
        self.assertIn("'gone'", errors[2])


class ShadowrocketProfileTest(unittest.TestCase):
    def test_ip_rule_without_equivalent_is_an_error(self):
        cfg = ProfileConfig.from_dict({"Name": "x", "DirectIp": ["geoip:private"], "BlockIp": ["203.0.113.0/24"]})
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "203.0.113.0/24"):
            ShadowrocketEmitter(Path(tmp)).emit_profile("X", cfg, Path(tmp), repo="o/r", epoch="0", updated_str="")

    def test_settings_shadowrocket_cannot_follow_are_errors(self):
        # The .CONF hardcodes always-real-ip and resolve-then-match-IP; Happ/INCY would obey the profile instead
        for key, value in (("FakeDNS", "true"), ("DomainStrategy", "AsIs")):
            cfg = ProfileConfig.from_dict({"Name": "x", key: value})
            with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, key):
                ShadowrocketEmitter(Path(tmp)).emit_profile("X", cfg, Path(tmp), repo="o/r", epoch="0", updated_str="")


class IpListGateTest(unittest.TestCase):
    def test_download_must_be_a_cidr_list_of_enough_size(self):
        full = "# header\n" + "".join(f"10.0.{i}.0/24\n" for i in range(50))
        self.assertEqual(check_download("whitelist.txt", full), (50, None))
        self.assertIn("not a CIDR list", check_download("whitelist.txt", "<html>\n10.0.0.0/24\n")[1])
        self.assertIn("not a CIDR list", check_download("whitelist.txt", "")[1])
        self.assertIn("at least 40", check_download("whitelist.txt", "10.0.0.0/24\n")[1])
        # 1000+ CIDRs in the previous release: half of that replaces the fixed floor
        self.assertIn("at least 1000", check_download("whitelist.txt", full, last=2000)[1])
        self.assertIsNone(check_download("whitelist.txt", full, last=100)[1])

    def test_built_list_too_big_or_foreign(self):
        self.assertEqual(check_built_list("whitelist", "77.88.8.0/24\n2a02:6b8::/32\n"), [])
        errors = check_built_list("whitelist", "77.88.8.0/24\n0.0.0.0/0\n")
        self.assertEqual(len(errors), 2)  # over the address limit, and 8.8.8.8 goes DIRECT
        self.assertEqual(len(check_built_list("direct", "8.8.8.0/24\n")), 1)
        # A /13 (524k addresses) fits under the old 1M whitelist limit: twice today's whole list
        self.assertEqual(len(check_built_list("whitelist", "10.0.0.0/13\n")), 1)

    def test_failed_check_keeps_yesterdays_baseline(self):
        # list-counts.txt is tomorrow's baseline: written after a failure, a truncated size would
        # lower the half-of-previous floor for good
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            d = Path(tmp)
            for name, floor in MIN_CIDRS.items():
                (d / name).write_text("".join(f"10.{i >> 8 & 255}.{i & 255}.0/24\n" for i in range(floor)))
            baseline = d / "list-counts.txt"
            self.assertEqual(check_downloads(d, None, accept=False), [])
            self.assertIn("refilter.txt 10000\n", baseline.read_text())
            self.assertEqual(check_downloads(d, baseline, accept=False), [])  # reads its own output back

            yesterday = d / "prev.txt"
            yesterday.write_text("refilter.txt 30000\n")
            baseline.unlink()
            errors = check_downloads(d, yesterday, accept=False)
            self.assertEqual(len(errors), 1)
            self.assertIn("at least 15000", errors[0])
            self.assertFalse(baseline.exists())
            self.assertEqual(check_downloads(d, yesterday, accept=True), [])  # a real drop, accepted by hand
            self.assertTrue(baseline.exists())

    def test_whitelist_must_stay_inside_ru_by(self):
        # whitelist.txt comes from a third-party repo and goes DIRECT: foreign ranges would bypass the VPN
        geo = ["77.88.0.0/18\n", "# custom\n5.255.255.0/24\n"]
        self.assertEqual(check_whitelist_geo("77.88.8.0/24\n5.255.255.0/24\n", geo), [])
        self.assertEqual(check_whitelist_geo("77.88.8.0/24\n151.236.93.0/24\n", geo), [])  # a few stray /24s
        errors = check_whitelist_geo("77.88.8.0/24\n104.16.0.0/13\n", geo)
        self.assertEqual(len(errors), 1)
        self.assertIn("104.16.0.0/13", errors[0])
        self.assertEqual(len(check_whitelist_geo("77.88.0.0/16\n", geo)), 1)  # 48k of the /16 lie outside the /18


class BuildTest(unittest.TestCase):
    def test_bad_inputs_stop_the_build(self):
        # Silently falling back would publish profile URLs and "now" instead of the pinned values
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HAPP").mkdir()
            (root / "HAPP/DEFAULT.JSON").write_text("{", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                build_all(root, repo="o/r")
            (root / "HAPP/DEFAULT.JSON").unlink()
            with self.assertRaisesRegex(ValueError, "abc"):
                build_all(root, repo="o/r", epoch="abc")


class ProfileConfigTest(unittest.TestCase):
    def test_unknown_key_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "ProxySite"):
            ProfileConfig.from_dict({"Name": "x", "ProxySite": ["geosite:youtube"]})

    def test_bad_values_are_rejected_on_load(self):
        # build loads profiles without lint: a bad value must not reach the emitted configs
        bad = {
            "Name": "",
            "FakeDNS": "ture",
            "RemoteDNSIP": "9.9.9",
            "DomesticDNSType": "DoQ",
            "DomainStrategy": "Bogus",
            "RouteOrder": "block-proxy-dirct",
            "DnsHosts": {"a.example": "nope"},
            "ProxySites": ["domain:example.org"],
            "BlockIp": ["10.0.0.0/33"],
        }
        with self.assertRaises(ValueError) as cm:
            ProfileConfig.from_dict(bad)
        for expected in ("Name", "FakeDNS", "RemoteDNSIP", "DomesticDNSType", "DomainStrategy", "RouteOrder",
                         "a.example", "domain:example.org", "10.0.0.0/33"):
            self.assertIn(expected, str(cm.exception))

    def test_known_keys_load(self):
        cfg = ProfileConfig.from_dict({
            "Name": "x",
            "ProxySites": ["geosite:youtube"],
            "GlobalProxy": True,
            "DnsHosts": {"a.example": "203.0.113.7"},
            "ProxyIp": ["10.0.0.1/24"],  # host bits set: clients accept it, so must we
        })
        self.assertEqual(cfg.proxy_sites, ["geosite:youtube"])
        self.assertEqual(cfg.global_proxy, "true")
        self.assertEqual(ProfileConfig.from_dict({}).name, "Default")


if __name__ == "__main__":
    unittest.main()
