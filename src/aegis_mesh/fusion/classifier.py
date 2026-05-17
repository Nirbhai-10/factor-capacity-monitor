"""Track classifier — softmax (multinomial logistic) regression trained on
synthetic, signature-structured samples (PLAN.md §2.3 classification).

Pure NumPy so it is deterministic and dependency-light. Trained once at
import from the same signature model the sim uses, then frozen. Real
deployment swaps this for the multi-modal CNN/transformer; the interface
(feature vector -> class probabilities) is what the rest of the stack uses.
"""

from __future__ import annotations

import numpy as np

from ..schemas import ObjectClass

CLASSES = [ObjectClass.UAS, ObjectClass.BIRD,
           ObjectClass.AIRCRAFT, ObjectClass.CLUTTER]
_IDX = {c: i for i, c in enumerate(CLASSES)}
FEATURES = ("log_speed", "alt100", "log_rcs", "micro_doppler",
            "rf_linked", "vert_frac")


def featurize(speed, alt, rcs, micro_doppler, rf_linked, vz) -> np.ndarray:
    return np.array([
        np.log1p(max(speed, 0.0)),
        alt / 100.0,
        np.log10(max(rcs, 1e-3)),
        float(micro_doppler),
        1.0 if rf_linked else 0.0,
        abs(vz) / (abs(speed) + 1e-3),
    ], dtype=float)


def _sample(rng, n):
    """Draw labelled feature samples from the sim's signature model."""
    X, y = [], []
    for _ in range(n):
        c = rng.integers(0, 4)
        if c == _IDX[ObjectClass.UAS]:
            quad = rng.random() < 0.6
            speed = rng.uniform(18, 30) if quad else rng.uniform(32, 45)
            alt = rng.uniform(60, 200)
            rcs = rng.lognormal(np.log(0.02 if quad else 0.15), 0.4)
            md = np.clip(rng.normal(0.85 if quad else 0.20, 0.1), 0, 1)
            rf = rng.random() < 0.6
            vz = rng.normal(0, 1.5)
        elif c == _IDX[ObjectClass.BIRD]:
            speed = rng.uniform(8, 18); alt = rng.uniform(20, 150)
            rcs = rng.lognormal(np.log(0.01), 0.5)
            md = np.clip(rng.normal(0.05, 0.04), 0, 1)
            rf = False; vz = rng.normal(0, 2.0)
        elif c == _IDX[ObjectClass.AIRCRAFT]:
            speed = rng.uniform(60, 140); alt = rng.uniform(200, 900)
            rcs = rng.lognormal(np.log(5.0), 0.5)
            md = np.clip(rng.normal(0.1, 0.05), 0, 1)
            rf = False; vz = rng.normal(0, 4.0)
        else:  # CLUTTER
            speed = rng.uniform(0, 8); alt = rng.uniform(10, 320)
            rcs = rng.lognormal(np.log(0.4), 0.7)
            md = rng.uniform(0, 0.15)
            rf = False; vz = rng.normal(0, 6.0)
        X.append(featurize(speed, alt, rcs, md, rf, vz))
        y.append(c)
    return np.array(X), np.array(y)


class SoftmaxClassifier:
    def __init__(self):
        self.mu = np.zeros(len(FEATURES))
        self.sd = np.ones(len(FEATURES))
        self.W = np.zeros((len(FEATURES) + 1, len(CLASSES)))

    def _design(self, X):
        Xn = (X - self.mu) / self.sd
        return np.hstack([Xn, np.ones((len(Xn), 1))])

    def fit(self, X, y, epochs=400, lr=0.5, l2=1e-4):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-6
        A = self._design(X)
        Y = np.eye(len(CLASSES))[y]
        n = len(X)
        for _ in range(epochs):
            Z = A @ self.W
            Z -= Z.max(1, keepdims=True)
            P = np.exp(Z); P /= P.sum(1, keepdims=True)
            grad = A.T @ (P - Y) / n + l2 * self.W
            self.W -= lr * grad
        return self

    def proba(self, feat: np.ndarray) -> dict[str, float]:
        a = np.hstack([(feat - self.mu) / self.sd, [1.0]])
        z = a @ self.W
        z -= z.max()
        p = np.exp(z); p /= p.sum()
        return {CLASSES[i].value: float(p[i]) for i in range(len(CLASSES))}


def _train_default() -> SoftmaxClassifier:
    rng = np.random.default_rng(7)
    Xtr, ytr = _sample(rng, 6000)
    return SoftmaxClassifier().fit(Xtr, ytr)


MODEL = _train_default()
