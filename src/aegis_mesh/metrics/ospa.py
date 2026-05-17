"""OSPA — Optimal Sub-Pattern Assignment metric (Schuhmacher, Vo & Vo,
IEEE T-SP 2008). The standard consistent multi-target tracking metric:
a per-object error combining a localisation term and a cardinality term,
with cut-off c and order p.

OSPA_c,p(X, Y), |X|=m <= n=|Y|:
  ( 1/n [ min_{pi} sum_i min(c, d(x_i, y_pi(i)))^p  +  c^p (n-m) ] )^(1/p)
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment


def ospa(X: np.ndarray, Y: np.ndarray, c: float = 150.0, p: float = 2.0):
    """X: estimated points (k,d), Y: truth points (m,d).
    Returns (ospa, localisation, cardinality)."""
    X = np.asarray(X, float).reshape(-1, X.shape[1] if X.ndim == 2 else 1) \
        if len(X) else np.zeros((0, Y.shape[1] if len(Y) else 2))
    nx, ny = len(X), len(Y)
    if nx == 0 and ny == 0:
        return 0.0, 0.0, 0.0
    if nx == 0 or ny == 0:
        return c, 0.0, c
    m, n = (nx, ny) if nx <= ny else (ny, nx)
    A, B = (X, Y) if nx <= ny else (Y, X)
    D = np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2)
    D = np.minimum(D, c)
    ri, ci = linear_sum_assignment(D ** p)
    loc = (D[ri, ci] ** p).sum()
    card = c ** p * (n - m)
    val = ((loc + card) / n) ** (1.0 / p)
    return (float(val), float((loc / n) ** (1.0 / p)),
            float((card / n) ** (1.0 / p)))
