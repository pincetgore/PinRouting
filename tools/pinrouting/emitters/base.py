"""Base emitter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pinrouting.models import ProfileConfig


class BaseEmitter(ABC):
    """Abstract base emitter for client configuration generators."""

    @abstractmethod
    def emit_profile(
        self,
        profile_id: str,
        profile: ProfileConfig,
        output_dir: Path,
        repo: str,
        epoch: Optional[str] = None,
    ) -> None:
        """Emit profile configuration files and links."""
        pass
