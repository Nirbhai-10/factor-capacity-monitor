"""Bertsekas auction algorithm with epsilon-scaling for the assignment
problem (LIDS-P-1653, 1987). Used for optimal weapon-target assignment of
the point effectors.

Solves max-benefit assignment of `n` targets to `m` effector slots. With
epsilon < 1/n (integer-scaled benefits) the assignment is optimal; we
epsilon-scale to resolve price wars efficiently. Infeasible pairs carry a
large negative benefit and are never chosen.
"""

from __future__ import annotations

import numpy as np

NEG = -1e15


def auction_assign(benefit: np.ndarray, eps0: float | None = None
                   ) -> np.ndarray:
    """benefit: (n_targets, m_slots). Returns assign[i] = slot or -1."""
    n, m = benefit.shape
    if n == 0 or m == 0:
        return np.full(n, -1, dtype=int)
    prices = np.zeros(m)
    assign = np.full(n, -1, dtype=int)
    owner = np.full(m, -1, dtype=int)
    span = float(np.max(benefit[benefit > NEG]) -
                 np.min(benefit[benefit > NEG])) if np.any(
        benefit > NEG) else 1.0
    eps = eps0 if eps0 is not None else max(span / 5.0, 1e-6)
    eps_min = 1.0 / (n + 1)

    while eps >= eps_min:
        assign[:] = -1
        owner[:] = -1
        prices[:] = 0.0
        unassigned = list(range(n))
        guard = 0
        while unassigned and guard < 200 * (n + m):
            guard += 1
            i = unassigned.pop()
            val = benefit[i] - prices                 # (m,)
            j = int(np.argmax(val))
            best = val[j]
            tmp = val.copy()
            tmp[j] = -np.inf
            second = float(np.max(tmp)) if m > 1 else best
            if benefit[i, j] <= NEG:                   # no feasible slot
                continue
            bid = (best - second) + eps
            prices[j] += bid
            prev = owner[j]
            if prev != -1:
                assign[prev] = -1
                unassigned.append(prev)
            owner[j] = i
            assign[i] = j
        eps /= 4.0
    return assign
