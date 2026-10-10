"""Data models and validation schemas for PinRouting profiles.

Adheres to official Happ & INCY specifications:
- Happ: https://www.happ.su/main/ru/dev-docs/routing
- INCY: https://incy.gitbook.io/docs/docs-en/routing
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

_CDN = "https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release"
_FLAGS = {"global_proxy", "use_chunk_files", "fake_dns"}  # "true" | "false" strings per Happ/INCY spec


def _key(json_key: str) -> dict[str, str]:
    return {"key": json_key}


@dataclass
class ProfileConfig:
    """Represents a unified routing profile according to Happ and INCY specs.

    Field order is the exact key order of the emitted Happ/INCY JSON.
    """

    name: str = field(metadata=_key("Name"))
    global_proxy: str = field(default="true", metadata=_key("GlobalProxy"))
    use_chunk_files: str = field(default="true", metadata=_key("UseChunkFiles"))
    remote_dns_type: str = field(default="DoH3", metadata=_key("RemoteDNSType"))
    remote_dns_domain: str = field(default="https://dns.quad9.net/dns-query", metadata=_key("RemoteDNSDomain"))
    remote_dns_ip: str = field(default="9.9.9.9", metadata=_key("RemoteDNSIP"))
    domestic_dns_type: str = field(default="DoH", metadata=_key("DomesticDNSType"))
    domestic_dns_domain: str = field(
        default="https://common.dot.dns.yandex.net/dns-query", metadata=_key("DomesticDNSDomain")
    )
    domestic_dns_ip: str = field(default="77.88.8.8", metadata=_key("DomesticDNSIP"))
    geoip_url: str = field(default=f"{_CDN}/geoip.dat", metadata=_key("Geoipurl"))
    geosite_url: str = field(default=f"{_CDN}/geosite.dat", metadata=_key("Geositeurl"))
    last_updated: str | None = field(default=None, metadata=_key("LastUpdated"))
    dns_hosts: dict[str, str] = field(default_factory=dict, metadata=_key("DnsHosts"))
    route_order: str = field(default="block-proxy-direct", metadata=_key("RouteOrder"))
    direct_sites: list[str] = field(default_factory=list, metadata=_key("DirectSites"))
    direct_ip: list[str] = field(default_factory=list, metadata=_key("DirectIp"))
    proxy_sites: list[str] = field(default_factory=list, metadata=_key("ProxySites"))
    proxy_ip: list[str] = field(default_factory=list, metadata=_key("ProxyIp"))
    block_sites: list[str] = field(default_factory=list, metadata=_key("BlockSites"))
    block_ip: list[str] = field(default_factory=list, metadata=_key("BlockIp"))
    domain_strategy: str = field(default="IPIfNonMatch", metadata=_key("DomainStrategy"))
    fake_dns: str = field(default="false", metadata=_key("FakeDNS"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileConfig:
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            if f.metadata["key"] in data:
                value = data[f.metadata["key"]]
                kwargs[f.name] = str(value).lower() if f.name in _FLAGS else value
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
