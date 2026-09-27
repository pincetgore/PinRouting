"""Build command: compiles profiles into HAPP, INCY, and SHADOWROCKET configurations."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from pinrouting.emitters.happ import HappEmitter
from pinrouting.emitters.incy import IncyEmitter
from pinrouting.emitters.shadowrocket import ShadowrocketEmitter
from pinrouting.models import ProfileConfig


def build_all(root_dir: Path, repo: str, epoch: Optional[str] = None) -> None:
    profiles_dir = root_dir / "profiles"
    happ_dir = root_dir / "HAPP"
    incy_dir = root_dir / "INCY"
    shadowrocket_dir = root_dir / "SHADOWROCKET"

    happ_emitter = HappEmitter()
    incy_emitter = IncyEmitter()
    sr_emitter = ShadowrocketEmitter(root_dir)

    # 1. Build Shadowrocket rulesets
    print("Building Shadowrocket rulesets...")
    counts = sr_emitter.build_all_rulesets(repo=repo)
    for name, cnt in sorted(counts.items()):
        print(f"  - {name}: {cnt} rules")

    # 2. Build Profiles
    profile_files = sorted(profiles_dir.glob("*.json"))
    if not profile_files:
        raise FileNotFoundError(f"No profile files found in {profiles_dir}")

    for pf in profile_files:
        profile_id = pf.stem.upper()
        print(f"\nProcessing profile: {profile_id} ({pf.name})...")
        cfg = ProfileConfig.load_from_file(pf)

        happ_emitter.emit_profile(
            profile_id, cfg, happ_dir, repo=repo, epoch=epoch
        )
        print(f"  ✓ Emitted HAPP: {profile_id}.JSON, .DEEPLINK")

        incy_emitter.emit_profile(
            profile_id, cfg, incy_dir, repo=repo, epoch=epoch
        )
        print(f"  ✓ Emitted INCY: {profile_id}.JSON, .DEEPLINK, .AUTOLINK")

        sr_emitter.emit_profile(
            profile_id, cfg, shadowrocket_dir, repo=repo, epoch=epoch
        )
        print(f"  ✓ Emitted SHADOWROCKET: {profile_id}.CONF")

    print("\n✓ All client configurations generated successfully!")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build PinRouting configurations for HAPP, INCY, and Shadowrocket"
    )
    parser.add_argument(
        "--repo",
        default="pincetgore/PinRouting",
        help="GitHub repository name in format owner/repo",
    )
    parser.add_argument(
        "--epoch",
        default=None,
        help="Unix timestamp for LastUpdated field (defaults to current if not provided in CI)",
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path.cwd()),
        help="Root directory of PinRouting workspace",
    )
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    build_all(root, repo=args.repo, epoch=args.epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
