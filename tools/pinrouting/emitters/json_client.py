"""Happ / INCY emitter: both clients share the same routing JSON and deeplink format.

Specifications:
- Happ: https://www.happ.su/main/ru/dev-docs/routing
- INCY routing: https://incy.gitbook.io/docs/docs-en/routing
- INCY autorouting: https://incy.gitbook.io/docs/docs-en/autorouting
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from pinrouting.models import ProfileConfig


def emit_json_profile(
    key: str,
    profile: ProfileConfig,
    output_dir: Path,
    scheme: str,
    epoch: str | None = None,
) -> None:
    """Write <key>.JSON and <key>.DEEPLINK (<scheme>://routing/onadd/{base64})."""
    output_dir.mkdir(parents=True, exist_ok=True)
    data = profile.to_client_dict(epoch=epoch)

    with open(output_dir / f"{key}.JSON", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    minified = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    b64 = base64.b64encode(minified.encode("utf-8")).decode("utf-8")
    with open(output_dir / f"{key}.DEEPLINK", "w", encoding="utf-8") as f:
        f.write(f"{scheme}://routing/onadd/{b64}\n")


def emit_incy_autolink(key: str, output_dir: Path, repo: str) -> None:
    """Write <key>.AUTOLINK (incy://autorouting/onadd/{raw JSON url})."""
    raw_url = f"https://raw.githubusercontent.com/{repo}/main/INCY/{key}.JSON"
    with open(output_dir / f"{key}.AUTOLINK", "w", encoding="utf-8") as f:
        f.write(f"incy://autorouting/onadd/{raw_url}\n")
