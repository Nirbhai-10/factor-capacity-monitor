"""Passive-emitter geolocation for the RF mesh.

- AOA least-squares triangulation: stack bearing constraints
  sin(b)*(x-xi) - cos(b)*(y-yi) = 0 and solve for (x,y); covariance from
  the linearised normal equations.
- Chan & Ho closed-form TDOA (IEEE T-SP 1994, "A simple and efficient
  estimator for hyperbolic location") when range-difference data exist.

Battle-grade rationale: one passive node gives only a bearing; the
distributed RF mesh must fuse bearings/TDOA into a position fix (with
covariance) so the multi-target filter gets metric measurements for the
RF-emitting (jam-resistant link, but not silent) threats.
"""

from __future__ import annotations

import numpy as np


def aoa_triangulate(sites: np.ndarray, az: np.ndarray,
                    ang_std: np.ndarray):
    """sites: (N,2) xy, az: (N,) bearings (rad). Returns (xy(2,), P(2,2))
    or None if ill-conditioned (e.g. < 2 sites / colinear bearings)."""
    if len(sites) < 2:
        return None
    A = np.stack([np.sin(az), -np.cos(az)], axis=1)          # (N,2)
    b = np.sin(az) * sites[:, 0] - np.cos(az) * sites[:, 1]  # (N,)
    w = 1.0 / np.maximum(ang_std, 1e-3) ** 2
    AtW = A.T * w
    N = AtW @ A
    if np.linalg.cond(N) > 1e8:
        return None
    xy = np.linalg.solve(N, AtW @ b)
    # range-scaled angular noise -> position covariance
    rng = np.linalg.norm(sites - xy, axis=1) + 1.0
    sigma = np.median(ang_std * rng)
    P = np.linalg.inv(N) * sigma ** 2 + np.eye(2) * 1.0
    return xy, P


def chan_ho_tdoa(sites: np.ndarray, r: np.ndarray, sigma: float = 15.0):
    """Closed-form TDOA fix. sites:(N,2) with sites[0] the reference;
    r:(N-1,) range differences d_i - d_0 (metres). Returns (xy, P)."""
    M = len(sites)
    if M < 4:
        return None
    x0, y0 = sites[0]
    s = sites[1:] - sites[0]                                   # (M-1,2)
    K = (s[:, 0] ** 2 + s[:, 1] ** 2)
    Ga = -np.stack([s[:, 0], s[:, 1], r], axis=1)              # (M-1,3)
    h = 0.5 * (r ** 2 - K)
    try:
        Z = np.linalg.lstsq(Ga, h, rcond=None)[0]              # [x',y',R0]
    except np.linalg.LinAlgError:
        return None
    xy = np.array([Z[0] + x0, Z[1] + y0])
    P = np.eye(2) * (sigma ** 2)
    return xy, P
