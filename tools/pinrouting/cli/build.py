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
    root_dir: Path, repo: str, epoch: str | None = None, geoip_text_dir: Path | None = None
) -> None:
    profiles_dir = root_dir / "profiles"
    happ_dir = root_dir / "HAPP"
    incy_dir = root_dir / "INCY"
    shadowrocket_dir = root_dir / "SHADOWROCKET"

    # If epoch is None, preserve existing LastUpdated from HAPP/DEFAULT.JSON to avoid diff churn
    if epoch is None:
        default_happ = happ_dir / "DEFAULT.JSON"
        if default_happ.is_file():
            try:
                with open(default_happ, "r", encoding="utf-8") as f:
                    epoch = json.load(f).get("LastUpdated")
            except (json.JSONDecodeError, OSError):
                pass
    if epoch is not None:
        epoch = str(epoch)

    # Format consistent updated_str for ruleset headers
    updated_str: str | None = None
    if epoch:
        try:
            dt = datetime.datetime.fromtimestamp(int(epoch), tz=datetime.UTC)
            updated_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, TypeError):
            pass

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
            epoch=epoch,
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
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    geoip_text_dir = Path(args.geoip_text_dir).resolve() if args.geoip_text_dir else None
    build_all(root, repo=args.repo, epoch=args.epoch, geoip_text_dir=geoip_text_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
