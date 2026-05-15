"""India / NSE cash-equity tax stack.

Reference (FY2025-26, equity delivery + intraday):
- STT: 0.1% on both buy & sell for delivery; 0.025% on sell for intraday
- Stamp duty: 0.015% on buy
- SEBI charges: ₹10 per crore (0.0001%)
- Exchange transaction charges (NSE cash): ~0.00345%
- GST: 18% on (brokerage + SEBI + exchange charges)
- Brokerage: assumed via `commission_bps` upstream

For a long-short factor strategy we treat all trades as 'delivery' (T+1
settlement) on the long leg and 'SLB-borrow' on the short leg — STT on
the short side is the same 0.1%, the borrow leg picks up an additional
fee modelled in `borrow.py`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def india_tax_bps(
    trade_dollars: pd.Series,
    side: str,           # 'buy' or 'sell'
    cfg,                 # Config.costs.india block
    brokerage_bps: float = 1.0,
) -> pd.Series:
    """Per-name tax cost as a fraction of trade value (not bps).

    `trade_dollars` is the *signed* leg — only |trade_dollars| matters for cost.
    """
    notional = trade_dollars.abs()
    if not cfg.enable:
        return pd.Series(0.0, index=notional.index)

    stt = cfg.stt_delivery_pct                # 0.001
    stamp = cfg.stamp_pct if side == "buy" else 0.0
    sebi = cfg.sebi_per_cr / 1e7              # ₹10/cr → fraction
    exch = cfg.exchange_pct
    gst_pct = cfg.gst_pct

    brokerage = brokerage_bps / 10_000.0

    # GST applies on (brokerage + SEBI + exchange charges)
    gst = gst_pct * (brokerage + sebi + exch)

    total_pct = stt + stamp + sebi + exch + gst
    return pd.Series(total_pct, index=notional.index)
