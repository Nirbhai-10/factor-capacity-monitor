"""Configuration loader. Reads YAML into a dict-of-dicts wrapper."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Config:
    """Thin wrapper around the YAML dict so call-sites can do `cfg.market.profile`."""

    _data: dict

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            raise AttributeError(key)
        if key not in self._data:
            raise AttributeError(f"Config has no key '{key}'")
        v = self._data[key]
        return _wrap(v)

    def __getitem__(self, key: str) -> Any:
        return _wrap(self._data[key])

    def get(self, key: str, default: Any = None) -> Any:
        return _wrap(self._data.get(key, default))

    def to_dict(self) -> dict:
        return dict(self._data)

    def keys(self):
        return self._data.keys()

    def items(self):
        for k, v in self._data.items():
            yield k, _wrap(v)

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, key) -> bool:
        return key in self._data


def _wrap(v: Any) -> Any:
    if isinstance(v, dict):
        return Config(v)
    return v


def load_config(path: str | Path | None = None) -> Config:
    """Load YAML config. Defaults to `config/default.yaml` from repo root."""
    if path is None:
        repo_root = Path(__file__).resolve().parents[2]
        path = repo_root / "config" / "default.yaml"
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return Config(data)
