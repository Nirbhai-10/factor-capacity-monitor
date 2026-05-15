"""Multi-factor capacity allocation.

Given a set of single-factor capacity curves and a total target AUM,
allocate AUM across factors to maximise total expected net annual return.

Mathematical setup:

    Let curve_k be a piecewise-linear (AUM, net_return_$) function for factor k.
    Then for an allocation w_k = AUM_k / TOTAL_AUM:

        net_return_$_k(AUM_k) = curve_k.net_return_ann × AUM_k    (interp on curve)

    maximise   Σ_k  net_return_$_k(w_k × TOTAL)
    s.t.       Σ_k w_k ≤ 1,  w_k ≥ 0
              (optionally) crowding_score_k ≤ s_max

Since net-return-as-a-function-of-AUM is *non-monotonic* (it rises until the
cost curve overtakes alpha), we solve by exhaustive search over a fine
allocation grid — the search is in K dimensions but fast because each curve
evaluation is just an interpolation.

For K ≤ 4 factors and 21 grid points per dim ≈ 200k combinations, this is
< 0.1s. Above that we'd switch to coordinate descent.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .curve import CapacityCurve


@dataclass
class AllocationResult:
    weights: dict[str, float]
    aum_allocations: dict[str, float]
    expected_net_return_dollars: float
    expected_net_return_pct: float
    factor_irs: dict[str, float]


def _interp_curve(curve: CapacityCurve, aum: float, field: str) -> float:
    df = curve.to_frame().sort_values("aum")
    if aum <= df.aum.iloc[0]:
        return float(df[field].iloc[0])
    if aum >= df.aum.iloc[-1]:
        return float(df[field].iloc[-1])
    return float(np.interp(aum, df.aum.values, df[field].values))


def allocate_multifactor(
    curves: dict[str, CapacityCurve],
    total_aum: float,
    crowding_scores: dict[str, float] | None = None,
    max_crowding_score: float = 100.0,
    grid_points: int = 21,
) -> AllocationResult:
    """Find weights that maximise expected net return $."""
    factor_names = [k for k, c in curves.items()
                    if (crowding_scores is None
                        or crowding_scores.get(k, 0) <= max_crowding_score)]
    if not factor_names:
        return AllocationResult({}, {}, 0.0, 0.0, {})

    K = len(factor_names)
    base = np.linspace(0, 1, grid_points)

    # Generate the simplex (sum w ≤ 1) by Cartesian product, filtered
    # For K=4, 21^4 = 194k points — fine.
    grids = np.meshgrid(*[base] * K, indexing="ij")
    flat = np.stack([g.flatten() for g in grids], axis=1)        # (N, K)
    mask = flat.sum(axis=1) <= 1 + 1e-9
    flat = flat[mask]

    best_obj = -np.inf
    best_w = None
    for w in flat:
        obj = 0.0
        for i, name in enumerate(factor_names):
            aum_k = w[i] * total_aum
            if aum_k <= 0:
                continue
            ret_pct = _interp_curve(curves[name], aum_k, "net_return_ann")
            obj += ret_pct * aum_k
        if obj > best_obj:
            best_obj = obj
            best_w = w

    weights = {n: float(best_w[i]) for i, n in enumerate(factor_names)}
    aum_alloc = {n: weights[n] * total_aum for n in factor_names}
    irs = {n: _interp_curve(curves[n], aum_alloc[n], "net_ir") for n in factor_names}

    return AllocationResult(
        weights=weights,
        aum_allocations=aum_alloc,
        expected_net_return_dollars=float(best_obj),
        expected_net_return_pct=float(best_obj / total_aum) if total_aum > 0 else 0,
        factor_irs=irs,
    )
