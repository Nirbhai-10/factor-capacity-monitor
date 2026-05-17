"""Predict 'safe AUM' from market-state features using ridge regression.

Trained per factor on rolling windows of the historical capacity scan. The
model lets us predict future safe-AUM without re-running the full curve scan
each day — useful for dashboards and live monitoring.

Features per training row:
    x_1: median spread (bps)              [liquidity]
    x_2: median realised vol (annualised) [vol regime]
    x_3: log10 median ADV ($)             [size of market]
    x_4: composite crowding score (0-100) [crowding]
    x_5: gross IR over the window         [signal strength]

Target:
    y: safe AUM (log10 ₹) over the same window

Ridge solution:
    β̂ = (XᵀX + λI)⁻¹ Xᵀy

We pick λ via leave-one-out cross-validation on a small grid.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CapacityModel:
    coefficients: dict[str, float]
    intercept: float
    lambda_: float
    r2_in_sample: float
    feature_names: list[str]

    def predict(self, features: dict[str, float]) -> float:
        """Predict safe AUM (₹) given a feature dict."""
        x = np.array([features[f] for f in self.feature_names])
        log_aum = self.intercept + float(np.dot(list(self.coefficients.values()), x))
        return float(10 ** log_aum)

    def explain(self, features: dict[str, float]) -> pd.DataFrame:
        """Per-feature contribution in log10(AUM) units."""
        rows = []
        for f in self.feature_names:
            beta = self.coefficients[f]
            x = features[f]
            rows.append({"feature": f, "value": x, "beta": beta, "contribution": beta * x})
        rows.append({"feature": "intercept", "value": 1.0,
                      "beta": self.intercept, "contribution": self.intercept})
        return pd.DataFrame(rows)


def _ridge(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Closed-form ridge with intercept absorbed via centering."""
    n, p = X.shape
    Xc = X - X.mean(axis=0)
    yc = y - y.mean()
    A = Xc.T @ Xc + lam * np.eye(p)
    beta = np.linalg.solve(A, Xc.T @ yc)
    intercept = y.mean() - X.mean(axis=0) @ beta
    return np.concatenate([[intercept], beta])


def _r2(y: np.ndarray, yhat: np.ndarray) -> float:
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def fit_capacity_ridge(
    feature_panel: pd.DataFrame,        # rows = training samples, cols = feature_names + 'safe_aum'
    feature_names: list[str],
    target_col: str = "safe_aum",
    lambdas: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0, 100.0),
) -> CapacityModel:
    """Fit ridge with leave-one-out lambda selection."""
    df = feature_panel.dropna(subset=feature_names + [target_col])
    if len(df) < len(feature_names) + 2:
        # Degenerate: not enough rows. Return a no-op model that returns the mean.
        mean_log_aum = (
            np.log10(df[target_col].replace(0, np.nan).dropna().mean())
            if df[target_col].notna().any() else 6.0
        )
        return CapacityModel(
            coefficients={f: 0.0 for f in feature_names},
            intercept=float(mean_log_aum),
            lambda_=0.0,
            r2_in_sample=0.0,
            feature_names=feature_names,
        )

    X = df[feature_names].values.astype(float)
    y = np.log10(df[target_col].clip(lower=1.0).values.astype(float))

    # LOO CV
    best_lam, best_err = None, np.inf
    for lam in lambdas:
        errs = []
        for i in range(len(X)):
            mask = np.ones(len(X), dtype=bool)
            mask[i] = False
            coef = _ridge(X[mask], y[mask], lam)
            pred = coef[0] + X[i] @ coef[1:]
            errs.append((pred - y[i]) ** 2)
        mse = float(np.mean(errs))
        if mse < best_err:
            best_err = mse
            best_lam = lam

    coef = _ridge(X, y, best_lam)
    intercept = float(coef[0])
    betas = coef[1:]
    yhat = intercept + X @ betas

    return CapacityModel(
        coefficients={f: float(b) for f, b in zip(feature_names, betas)},
        intercept=intercept,
        lambda_=float(best_lam),
        r2_in_sample=_r2(y, yhat),
        feature_names=feature_names,
    )
