"""Interacting Multiple Model (IMM) estimator — CV + coordinated-turn bank.

Blom & Bar-Shalom, IEEE TAC 1988. Standard 4-step recursion: mixing ->
mode-matched filtering -> mode-probability update -> combination.

Mode bank: a constant-velocity model plus fixed-rate coordinated-turn
models (±Omega). Fixed-rate CT keeps every model linear and avoids the
weakly-observable turn-rate-as-state EKF — the robust, fielded design.

Battle-grade rationale: attack drones jink/turn; a single CV filter lags
in maneuvers. The IMM blends cruise and turn models by data-driven mode
probabilities, cutting maneuver track error and loss.
"""

from __future__ import annotations

import numpy as np

from .models import F_cv, F_ct, H_POS, Q_disc

State = 4


class IMM:
    def __init__(self, s0: np.ndarray, P0: np.ndarray,
                 turn_rates=(0.0, 0.12, -0.12), q_acc: float = 6.0,
                 p_stay: float = 0.92):
        self.W = list(turn_rates)
        self.q = q_acc
        n = len(self.W)
        self.x = [np.array(s0, float).copy() for _ in range(n)]
        self.P = [np.array(P0, float).copy() for _ in range(n)]
        self.mu = np.full(n, 1.0 / n)
        off = (1.0 - p_stay) / (n - 1)
        self.Pi = np.full((n, n), off) + np.eye(n) * (p_stay - off)

    def _mix(self):
        n = len(self.W)
        cbar = np.clip(self.Pi.T @ self.mu, 1e-9, None)
        w = (self.Pi * self.mu[:, None]) / cbar[None, :]
        x0, P0 = [], []
        for j in range(n):
            xj = sum(w[i, j] * self.x[i] for i in range(n))
            Pj = np.zeros((State, State))
            for i in range(n):
                d = (self.x[i] - xj).reshape(-1, 1)
                Pj += w[i, j] * (self.P[i] + d @ d.T)
            x0.append(xj)
            P0.append(Pj)
        return x0, P0, cbar

    def step(self, z: np.ndarray, dt: float, R: np.ndarray) -> None:
        x0, P0, cbar = self._mix()
        Q = Q_disc(dt, self.q)
        like = np.zeros(len(self.W))
        for j, wr in enumerate(self.W):
            F = F_cv(dt) if wr == 0.0 else F_ct(wr, dt)
            xp = F @ x0[j]
            Pp = F @ P0[j] @ F.T + Q
            y = z - H_POS @ xp
            S = H_POS @ Pp @ H_POS.T + R
            Si = np.linalg.inv(S)
            K = Pp @ H_POS.T @ Si
            self.x[j] = xp + K @ y
            self.P[j] = (np.eye(State) - K @ H_POS) @ Pp
            det = max(np.linalg.det(2 * np.pi * S), 1e-12)
            like[j] = np.exp(-0.5 * float(y @ Si @ y)) / np.sqrt(det)
        m = cbar * like
        self.mu = m / max(m.sum(), 1e-12)

    @property
    def estimate(self) -> np.ndarray:
        return sum(self.mu[i] * self.x[i] for i in range(len(self.W)))

    @property
    def cov(self) -> np.ndarray:
        xc = self.estimate
        P = np.zeros((State, State))
        for i in range(len(self.W)):
            d = (self.x[i] - xc).reshape(-1, 1)
            P += self.mu[i] * (self.P[i] + d @ d.T)
        return P

    @property
    def maneuvering(self) -> bool:
        # any turn model more probable than the cruise (CV) model
        cv = next(i for i, w in enumerate(self.W) if w == 0.0)
        return self.mu.sum() - self.mu[cv] > self.mu[cv]
