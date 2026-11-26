"""Data models and validation schemas for PinRouting profiles.

Adheres to official Happ & INCY specifications:
- Happ: https://www.happ.su/main/ru/dev-docs/routing
- INCY: https://incy.gitbook.io/docs/docs-en/routing
"""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Literal, get_args, get_origin, get_type_hints

_CDN = "https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release"

Flag = Literal["true", "false"]  # strings, not booleans, per Happ/INCY spec
DnsType = Literal["DoH", "DoH3", "DoU", "DoT"]
DomainStrategy = Literal["AsIs", "IPIfNonMatch", "IPOnDemand"]
# The only order the Shadowrocket emitter and the routing tests implement; teach both before adding another
RouteOrder = Literal["block-proxy-direct"]


class ProfileError(ValueError):
    """Every problem found in one profile, so a single run reports them all."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


def _key(json_key: str) -> dict[str, str]:
    return {"key": json_key}


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _is_cidr(value: str) -> bool:
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        return False
    return True


@dataclass
class ProfileConfig:
    """Represents a unified routing profile according to Happ and INCY specs.

    Field order is the exact key order of the emitted Happ/INCY JSON.
    """

    name: str = field(metadata=_key("Name"))
    global_proxy: Flag = field(default="true", metadata=_key("GlobalProxy"))
    use_chunk_files: Flag = field(default="true", metadata=_key("UseChunkFiles"))
    remote_dns_type: DnsType = field(default="DoH3", metadata=_key("RemoteDNSType"))
    remote_dns_domain: str = field(default="https://dns.quad9.net/dns-query", metadata=_key("RemoteDNSDomain"))
    remote_dns_ip: str = field(default="9.9.9.9", metadata=_key("RemoteDNSIP"))
    domestic_dns_type: DnsType = field(default="DoH", metadata=_key("DomesticDNSType"))
    domestic_dns_domain: str = field(
        default="https://common.dot.dns.yandex.net/dns-query", metadata=_key("DomesticDNSDomain")
    )
    domestic_dns_ip: str = field(default="77.88.8.8", metadata=_key("DomesticDNSIP"))
    geoip_url: str = field(default=f"{_CDN}/geoip.dat", metadata=_key("Geoipurl"))
    geosite_url: str = field(default=f"{_CDN}/geosite.dat", metadata=_key("Geositeurl"))
    last_updated: str | None = field(default=None, metadata=_key("LastUpdated"))
    dns_hosts: dict[str, str] = field(default_factory=dict, metadata=_key("DnsHosts"))
    route_order: RouteOrder = field(default="block-proxy-direct", metadata=_key("RouteOrder"))
    direct_sites: list[str] = field(default_factory=list, metadata=_key("DirectSites"))
    direct_ip: list[str] = field(default_factory=list, metadata=_key("DirectIp"))
    proxy_sites: list[str] = field(default_factory=list, metadata=_key("ProxySites"))
    proxy_ip: list[str] = field(default_factory=list, metadata=_key("ProxyIp"))
    block_sites: list[str] = field(default_factory=list, metadata=_key("BlockSites"))
    block_ip: list[str] = field(default_factory=list, metadata=_key("BlockIp"))
    domain_strategy: DomainStrategy = field(default="IPIfNonMatch", metadata=_key("DomainStrategy"))
    fake_dns: Flag = field(default="false", metadata=_key("FakeDNS"))

    def __post_init__(self) -> None:
        problems = self.problems()
        if problems:
            raise ProfileError(problems)

    def problems(self) -> list[str]:
        """Checks that need nothing but the profile; geosite/geoip existence is checked by lint."""
        return self._setting_problems() + self._rule_problems()

    def _setting_problems(self) -> list[str]:
        problems = [] if self.name else ["Profile Name cannot be empty"]
        for f in fields(self):
            allowed = _CHOICES.get(f.name)
            value = getattr(self, f.name)
            if allowed and value not in allowed:
                problems.append(f"{f.metadata['key']} '{value}' is not one of: {', '.join(allowed)}")
        dns_ips = {"RemoteDNSIP": self.remote_dns_ip, "DomesticDNSIP": self.domestic_dns_ip}
        problems += [f"{label} '{ip}' is not an IP address" for label, ip in dns_ips.items() if not _is_ip(ip)]
        problems += [f"Invalid IP '{ip}' for host '{d}' in DnsHosts" for d, ip in self.dns_hosts.items() if not _is_ip(ip)]
        return problems

    def _rule_problems(self) -> list[str]:
        # The Shadowrocket emitter and the routing tests only understand geosite: categories
        problems = [
            f"Site rule '{s}' must be 'geosite:<category>'"
            for s in self.direct_sites + self.proxy_sites + self.block_sites
            if not s.startswith("geosite:")
        ]
        return problems + [
            f"Invalid CIDR rule '{r}'"
            for r in self.direct_ip + self.proxy_ip + self.block_ip
            if not r.startswith("geoip:") and not _is_cidr(r)
        ]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileConfig:
        # A typo like "ProxySite" would otherwise silently ship a profile without those rules
        unknown = data.keys() - {f.metadata["key"] for f in fields(cls)}
        if unknown:
            raise ProfileError([f"Unknown profile key(s): {', '.join(sorted(unknown))}"])
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            if f.metadata["key"] in data:
                value = data[f.metadata["key"]]
                kwargs[f.name] = str(value).lower() if _CHOICES.get(f.name) == get_args(Flag) else value
        kwargs.setdefault("name", "Default")
        return cls(**kwargs)

    @classmethod
    def load_from_file(cls, path: Path | str) -> ProfileConfig:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_client_dict(self, epoch: str | None = None) -> dict[str, Any]:
        """Convert to the standard Happ/INCY JSON dictionary structure preserving exact key order."""
        out: dict[str, Any] = {f.metadata["key"]: getattr(self, f.name) for f in fields(self)}
        last_updated = epoch if epoch is not None else self.last_updated
        if last_updated is None:
            del out["LastUpdated"]
        else:
            out["LastUpdated"] = str(last_updated)
        return out


# Allowed values come from the Literal annotations above: one place to add a DNS type or strategy
_CHOICES: dict[str, tuple[str, ...]] = {
    name: get_args(hint) for name, hint in get_type_hints(ProfileConfig).items() if get_origin(hint) is Literal
}
