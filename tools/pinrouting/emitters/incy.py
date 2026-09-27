"""INCY emitter: generates INCY/<ID>.JSON, INCY/<ID>.DEEPLINK, and INCY/<ID>.AUTOLINK.

Specification:
- Routing: https://incy.gitbook.io/docs/docs-en/routing
- Autorouting: https://incy.gitbook.io/docs/docs-en/autorouting
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from pinrouting.emitters.base import BaseEmitter
from pinrouting.models import ProfileConfig


class IncyEmitter(BaseEmitter):
    def emit_profile(
        self,
        profile_id: str,
        profile: ProfileConfig,
        output_dir: Path,
        repo: str,
        epoch: str | None = None,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        key = profile_id.upper()

        data = profile.to_client_dict(epoch=epoch)

        # 1. Write pretty JSON
        json_path = output_dir / f"{key}.JSON"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # 2. Write minified base64 deeplink (incy://routing/onadd/{base64})
        minified = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        b64 = base64.b64encode(minified.encode("utf-8")).decode("utf-8")
        deeplink_path = output_dir / f"{key}.DEEPLINK"
        with open(deeplink_path, "w", encoding="utf-8") as f:
            f.write(f"incy://routing/onadd/{b64}\n")

        # 3. Write autorouting link (incy://autorouting/onadd/{url})
        raw_url = f"https://raw.githubusercontent.com/{repo}/main/INCY/{key}.JSON"
        autolink_path = output_dir / f"{key}.AUTOLINK"
        with open(autolink_path, "w", encoding="utf-8") as f:
            f.write(f"incy://autorouting/onadd/{raw_url}\n")
