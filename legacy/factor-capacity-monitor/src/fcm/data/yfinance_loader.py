"""Real-data path: pull NIFTY-100 OHLCV from yfinance and assemble a MarketPanel.

Optional dependency — install with `pip install -e .[data]`.
Used by `scripts/fetch_data.py` to produce a cached parquet next to the
synthetic fixture.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .types import MarketPanel


# A small representative slice of NIFTY-100 (full list lives in config/nifty100.yaml).
NIFTY100_SAMPLE = [
    "RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "LT.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS", "TATAMOTORS.NS", "POWERGRID.NS",
]


def fetch_panel(
    tickers: Iterable[str] | None = None,
    period: str = "5y",
    cache_path: str | Path | None = None,
) -> MarketPanel:
    """Fetch a panel via yfinance. Lazy import — yfinance is optional."""
    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError(
            "yfinance not installed. Install via `pip install -e .[data]`."
        ) from e

    tickers = list(tickers) if tickers is not None else NIFTY100_SAMPLE
    if cache_path is not None:
        cache_path = Path(cache_path)
        if cache_path.exists():
            return _load_from_parquet(cache_path)

    df = yf.download(tickers, period=period, group_by="ticker", auto_adjust=True,
                      progress=False, threads=True)

    closes, opens, highs, lows, volumes = {}, {}, {}, {}, {}
    for t in tickers:
        if t not in df.columns.get_level_values(0):
            continue
        sub = df[t]
        closes[t] = sub["Close"]
        opens[t] = sub["Open"]
        highs[t] = sub["High"]
        lows[t] = sub["Low"]
        volumes[t] = sub["Volume"]

    close = pd.DataFrame(closes)
    open_ = pd.DataFrame(opens)
    high = pd.DataFrame(highs)
    low = pd.DataFrame(lows)
    volume = pd.DataFrame(volumes)
    dollar_volume = close * volume

    # Fundamentals: per-ticker `.info` is rate-limited and unreliable.
    # For now, fill with NaN — caller can plug a real source via screener.in
    # or ingest a separate fundamentals file.
    pb = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    roe = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    short_interest = pd.DataFrame(np.nan, index=close.index, columns=close.columns)

    panel = MarketPanel(
        close=close, high=high, low=low, open_=open_,
        volume=volume, dollar_volume=dollar_volume,
        pb=pb, roe=roe, short_interest=short_interest,
        sectors={t: "Unknown" for t in close.columns},
    )

    if cache_path is not None:
        _save_to_parquet(panel, cache_path)
    return panel


def _save_to_parquet(panel: MarketPanel, path: Path):
    path.mkdir(parents=True, exist_ok=True)
    for name, df in [
        ("close", panel.close), ("open", panel.open_),
        ("high", panel.high), ("low", panel.low),
        ("volume", panel.volume), ("dollar_volume", panel.dollar_volume),
        ("pb", panel.pb), ("roe", panel.roe),
        ("short_interest", panel.short_interest),
    ]:
        df.to_parquet(path / f"{name}.parquet")


def _load_from_parquet(path: Path) -> MarketPanel:
    def _r(n): return pd.read_parquet(path / f"{n}.parquet")
    return MarketPanel(
        close=_r("close"), open_=_r("open"), high=_r("high"), low=_r("low"),
        volume=_r("volume"), dollar_volume=_r("dollar_volume"),
        pb=_r("pb"), roe=_r("roe"), short_interest=_r("short_interest"),
        sectors={c: "Unknown" for c in _r("close").columns},
    )
