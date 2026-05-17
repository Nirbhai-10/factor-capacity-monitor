"""Runtime configuration (12-factor: env-overridable)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _b(k, d):
    return os.getenv(k, str(d)).lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    host: str = os.getenv("AEGIS_HOST", "0.0.0.0")
    port: int = int(os.getenv("AEGIS_PORT", "8000"))
    default_tracker: str = os.getenv("AEGIS_TRACKER", "gmphd")
    mitigation_authorized: bool = _b("AEGIS_MITIGATION", True)
    require_human: bool = _b("AEGIS_REQUIRE_HUMAN", False)
    playback_speed: float = float(os.getenv("AEGIS_PLAYBACK_SPEED", "6"))
    log_level: str = os.getenv("AEGIS_LOG_LEVEL", "INFO")


CONFIG = Config()
