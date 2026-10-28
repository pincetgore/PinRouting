"""Build command: compiles profiles into HAPP, INCY, and SHADOWROCKET configurations."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

from pinrouting.emitters.json_client import emit_incy_autolink, emit_json_profile
from pinrouting.emitters.shadowrocket import ShadowrocketEmitter
from pinrouting.models import ProfileConfig


def build_all(
    root_dir: Path,
    repo: str,
    epoch: str | None = None,
    geoip_text_dir: Path | None = None,
    geodata_ref: str | None = None,
) -> None:
    profiles_dir = root_dir / "profiles"
    happ_dir = root_dir / "HAPP"
    incy_dir = root_dir / "INCY"
    shadowrocket_dir = root_dir / "SHADOWROCKET"

    # Values not given on the command line are kept from the published HAPP/DEFAULT.JSON to avoid diff churn
    published: dict = {}
    default_happ = happ_dir / "DEFAULT.JSON"
    if default_happ.is_file():
        try:
            with open(default_happ, "r", encoding="utf-8") as f:
                published = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    if epoch is None:
        epoch = published.get("LastUpdated")
    if epoch is not None:
        epoch = str(epoch)

    # Geodata URLs pin a release-branch commit: jsDelivr serves @<sha> immutably, while @release
    # stayed stale for hours even after a purge
    if geodata_ref:
        base = f"https://cdn.jsdelivr.net/gh/{repo}@{geodata_ref}"
        geodata_urls = (f"{base}/geoip.dat", f"{base}/geosite.dat")
    elif "Geoipurl" in published and "Geositeurl" in published:
        geodata_urls = (published["Geoipurl"], published["Geositeurl"])
    else:
        geodata_urls = None  # first build: use the URLs from profiles/*.json

    # One timestamp for every Shadowrocket header; "now" when there is no (valid) epoch
    stamp = datetime.datetime.now(datetime.UTC)
    if epoch:
        try:
            stamp = datetime.datetime.fromtimestamp(int(epoch), tz=datetime.UTC)
        except (ValueError, TypeError):
            pass
    updated_str = stamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    sr_epoch = str(int(stamp.timestamp()))

    sr_emitter = ShadowrocketEmitter(root_dir)

    # 1. Build Shadowrocket rulesets
    print("Building Shadowrocket rulesets...")
    counts = sr_emitter.build_all_rulesets(repo=repo, updated_str=updated_str, geoip_text_dir=geoip_text_dir)
    for name, cnt in sorted(counts.items()):
        print(f"  - {name}: {cnt} rules")

    # 2. Build Profiles
    profile_files = sorted(profiles_dir.glob("*.json"))
    if not profile_files:
        raise FileNotFoundError(f"No profile files found in {profiles_dir}")

    for pf in profile_files:
        key = pf.stem.upper()
        print(f"\nProcessing profile: {key} ({pf.name})...")
        cfg = ProfileConfig.load_from_file(pf)
        if geodata_urls:
            cfg.geoip_url, cfg.geosite_url = geodata_urls

        emit_json_profile(key, cfg, happ_dir, scheme="happ", epoch=epoch)
        print(f"  ✓ Emitted HAPP: {key}.JSON, .DEEPLINK")

        emit_json_profile(key, cfg, incy_dir, scheme="incy", epoch=epoch)
        emit_incy_autolink(key, incy_dir, repo=repo)
        print(f"  ✓ Emitted INCY: {key}.JSON, .DEEPLINK, .AUTOLINK")

        sr_emitter.emit_profile(
            key,
            cfg,
            shadowrocket_dir,
            repo=repo,
            epoch=sr_epoch,
            updated_str=updated_str,
        )
        print(f"  ✓ Emitted SHADOWROCKET: {key}.CONF")

    print("\n✓ All client configurations generated successfully!")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pinrouting build",
        description="Build PinRouting configurations for HAPP, INCY, and Shadowrocket",
    )
    parser.add_argument(
        "--repo",
        default="pincetgore/PinRouting",
        help="GitHub repository name in format owner/repo",
    )
    parser.add_argument(
        "--epoch",
        default=None,
        help="Unix timestamp for LastUpdated field (defaults to the existing value in HAPP/DEFAULT.JSON)",
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path.cwd()),
        help="Root directory of PinRouting workspace",
    )
    parser.add_argument(
        "--geoip-text-dir",
        default=None,
        help="geoip builder output/text dir (direct.txt, whitelist.txt) to rebuild Shadowrocket IP lists; "
        "if omitted, existing IP lists are kept",
    )
    parser.add_argument(
        "--geodata-ref",
        default=None,
        help="release-branch commit to pin Geoipurl/Geositeurl to on jsDelivr "
        "(defaults to the URLs in the published HAPP/DEFAULT.JSON)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    geoip_text_dir = Path(args.geoip_text_dir).resolve() if args.geoip_text_dir else None
    build_all(
        root, repo=args.repo, epoch=args.epoch, geoip_text_dir=geoip_text_dir, geodata_ref=args.geodata_ref
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
