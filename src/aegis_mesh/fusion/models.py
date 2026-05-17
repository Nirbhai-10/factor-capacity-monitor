"""Planar motion models for the IMM filter.

State: s = [x, vx, y, vy]. Constant-velocity and *fixed-rate*
coordinated-turn transitions (both linear — the standard IMM-CT model
bank, robust vs. estimating the turn rate as a weakly-observable state).
"""

from __future__ import annotations

import numpy as np

H_POS = np.array([[1.0, 0, 0, 0],
                  [0, 0, 1.0, 0]])


def F_cv(dt: float) -> np.ndarray:
    F = np.eye(4)
    F[0, 1] = dt
    F[2, 3] = dt
    return F


def F_ct(w: float, dt: float) -> np.ndarray:
    """Fixed turn-rate w (rad/s) coordinated-turn transition."""
    if abs(w) < 1e-6:
        return F_cv(dt)
    s, c = np.sin(w * dt), np.cos(w * dt)
    return np.array([
        [1, s / w,        0, -(1 - c) / w],
        [0, c,            0, -s],
        [0, (1 - c) / w,  1, s / w],
        [0, s,            0, c],
    ])


def Q_disc(dt: float, q_acc: float) -> np.ndarray:
    blk = np.array([[dt**4 / 4, dt**3 / 2],
                    [dt**3 / 2, dt**2]]) * q_acc
    Q = np.zeros((4, 4))
    Q[:2, :2] = blk
    Q[2:, 2:] = blk
    return Q
