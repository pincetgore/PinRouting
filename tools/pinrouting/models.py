"""Data models and validation schemas for PinRouting profiles.

Adheres to official Happ & INCY specifications:
- Happ: https://www.happ.su/main/ru/dev-docs/routing
- INCY: https://incy.gitbook.io/docs/docs-en/routing
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProfileConfig:
    """Represents a unified routing profile according to Happ and INCY specs."""

    name: str
    global_proxy: str = "true"  # "true" | "false"
    remote_dns_type: str = "DoH3"  # "DoH" | "DoH3" | "DoU" | "DoT"
    remote_dns_domain: str = "https://dns.quad9.net/dns-query"
    remote_dns_ip: str = "9.9.9.9"
    domestic_dns_type: str = "DoH"  # "DoH" | "DoH3" | "DoU"
    domestic_dns_domain: str = "https://common.dot.dns.yandex.net/dns-query"
    domestic_dns_ip: str = "77.88.8.8"
    geoip_url: str = (
        "https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geoip.dat"
    )
    geosite_url: str = (
        "https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geosite.dat"
    )
    dns_hosts: dict[str, str] = field(default_factory=dict)
    direct_sites: list[str] = field(default_factory=list)
    direct_ip: list[str] = field(default_factory=list)
    proxy_sites: list[str] = field(default_factory=list)
    proxy_ip: list[str] = field(default_factory=list)
    block_sites: list[str] = field(default_factory=list)
    block_ip: list[str] = field(default_factory=list)
    domain_strategy: str = "IPIfNonMatch"
    fake_dns: str = "false"
    use_chunk_files: str = "true"
    route_order: str = "block-proxy-direct"
    last_updated: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileConfig:
        return cls(
            name=data.get("Name", "Default"),
            global_proxy=str(data.get("GlobalProxy", "true")),
            remote_dns_type=data.get("RemoteDNSType", "DoH3"),
            remote_dns_domain=data.get(
                "RemoteDNSDomain", "https://dns.quad9.net/dns-query"
            ),
            remote_dns_ip=data.get("RemoteDNSIP", "9.9.9.9"),
            domestic_dns_type=data.get("DomesticDNSType", "DoH"),
            domestic_dns_domain=data.get(
                "DomesticDNSDomain",
                "https://common.dot.dns.yandex.net/dns-query",
            ),
            domestic_dns_ip=data.get("DomesticDNSIP", "77.88.8.8"),
            geoip_url=data.get(
                "Geoipurl",
                "https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geoip.dat",
            ),
            geosite_url=data.get(
                "Geositeurl",
                "https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geosite.dat",
            ),
            dns_hosts=dict(data.get("DnsHosts", {})),
            direct_sites=list(data.get("DirectSites", [])),
            direct_ip=list(data.get("DirectIp", [])),
            proxy_sites=list(data.get("ProxySites", [])),
            proxy_ip=list(data.get("ProxyIp", [])),
            block_sites=list(data.get("BlockSites", [])),
            block_ip=list(data.get("BlockIp", [])),
            domain_strategy=data.get("DomainStrategy", "IPIfNonMatch"),
            fake_dns=str(data.get("FakeDNS", "false")),
            use_chunk_files=str(
                data.get("UseChunkFiles", data.get("useChunkFiles", "true"))
            ).lower(),
            route_order=data.get("RouteOrder", "block-proxy-direct"),
            last_updated=data.get("LastUpdated"),
        )

    @classmethod
    def load_from_file(cls, path: Path | str) -> ProfileConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_client_dict(self, epoch: str | None = None) -> dict[str, Any]:
        """Convert to the standard Happ/INCY JSON dictionary structure preserving exact key order."""
        out: dict[str, Any] = {
            "Name": self.name,
            "GlobalProxy": self.global_proxy,
            "UseChunkFiles": self.use_chunk_files,
            "RemoteDNSType": self.remote_dns_type,
            "RemoteDNSDomain": self.remote_dns_domain,
            "RemoteDNSIP": self.remote_dns_ip,
            "DomesticDNSType": self.domestic_dns_type,
            "DomesticDNSDomain": self.domestic_dns_domain,
            "DomesticDNSIP": self.domestic_dns_ip,
            "Geoipurl": self.geoip_url,
            "Geositeurl": self.geosite_url,
        }

        # LastUpdated timestamp (Unix seconds)
        if epoch is not None:
            out["LastUpdated"] = str(epoch)
        elif self.last_updated is not None:
            out["LastUpdated"] = str(self.last_updated)

        out["DnsHosts"] = self.dns_hosts
        out["RouteOrder"] = self.route_order
        out["DirectSites"] = self.direct_sites
        out["DirectIp"] = self.direct_ip
        out["ProxySites"] = self.proxy_sites
        out["ProxyIp"] = self.proxy_ip
        out["BlockSites"] = self.block_sites
        out["BlockIp"] = self.block_ip
        out["DomainStrategy"] = self.domain_strategy
        out["FakeDNS"] = self.fake_dns

        return out
