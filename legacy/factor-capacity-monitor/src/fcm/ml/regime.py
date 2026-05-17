"""Cluster the market into 3 latent regimes via Gaussian Mixture (EM).

Features used (per business day):
    market vol (cross-sectional median realised vol)
    average pairwise correlation of returns
    median bid-ask spread
    median ADV (log)

Three components: 'calm', 'normal', 'stressed' (assigned post-fit by the
ranked centroids — highest-vol regime is 'stressed').

Implementation: small custom EM loop (no sklearn dependency) — keeps the
project deps minimal. Diagonal covariance for stability on short series.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RegimeClassification:
    labels: pd.Series                  # date → regime label
    probabilities: pd.DataFrame        # date × regime
    centroids: pd.DataFrame            # regime × feature  (interpretable)
    current_regime: str
    current_probabilities: dict[str, float]


_REGIME_NAMES = ["calm", "normal", "stressed"]


def _standardise(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    return (X - mu) / sd, mu, sd


def _gmm_em(
    X: np.ndarray, k: int, n_iter: int = 50, seed: int = 7
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Diagonal-covariance GMM via EM. Returns (means, vars, weights)."""
    rng = np.random.default_rng(seed)
    n, d = X.shape
    # Initialise with k-means++-style spread
    idx0 = rng.integers(0, n)
    centers = [X[idx0]]
    for _ in range(k - 1):
        dists = np.min(
            np.stack([((X - c) ** 2).sum(axis=1) for c in centers], axis=1),
            axis=1,
        )
        probs = dists / max(dists.sum(), 1e-9)
        idx = rng.choice(n, p=probs)
        centers.append(X[idx])
    means = np.array(centers)
    variances = np.tile(X.var(axis=0) + 1e-3, (k, 1))
    weights = np.ones(k) / k

    for _ in range(n_iter):
        # E-step
        log_resp = np.zeros((n, k))
        for j in range(k):
            diff = X - means[j]
            log_p = -0.5 * (
                np.sum(diff ** 2 / variances[j], axis=1)
                + np.log(2 * np.pi * variances[j]).sum()
            )
            log_resp[:, j] = np.log(max(weights[j], 1e-12)) + log_p
        log_resp -= log_resp.max(axis=1, keepdims=True)
        resp = np.exp(log_resp)
        resp /= resp.sum(axis=1, keepdims=True) + 1e-12

        # M-step
        Nk = resp.sum(axis=0) + 1e-9
        weights = Nk / n
        for j in range(k):
            means[j] = (resp[:, j:j+1] * X).sum(axis=0) / Nk[j]
            variances[j] = ((resp[:, j:j+1] * (X - means[j]) ** 2).sum(axis=0)
                              / Nk[j]) + 1e-3
    return means, variances, weights


def _gmm_predict(X: np.ndarray, means, variances, weights) -> np.ndarray:
    n, d = X.shape
    k = means.shape[0]
    log_resp = np.zeros((n, k))
    for j in range(k):
        diff = X - means[j]
        log_p = -0.5 * (
            np.sum(diff ** 2 / variances[j], axis=1)
            + np.log(2 * np.pi * variances[j]).sum()
        )
        log_resp[:, j] = np.log(max(weights[j], 1e-12)) + log_p
    log_resp -= log_resp.max(axis=1, keepdims=True)
    resp = np.exp(log_resp)
    resp /= resp.sum(axis=1, keepdims=True) + 1e-12
    return resp


def classify_regime(panel, spreads: pd.DataFrame, k: int = 3) -> RegimeClassification:
    """Classify each date into a regime."""
    rets = panel.close.pct_change()
    vol = rets.rolling(20, min_periods=10).std() * np.sqrt(252)
    market_vol = vol.median(axis=1)

    # Average pairwise correlation in a 60-day rolling window
    def _avg_corr(window_ret: pd.DataFrame) -> float:
        if window_ret.shape[0] < 20 or window_ret.shape[1] < 5:
            return np.nan
        c = window_ret.corr().values
        return float(np.nanmean(c[np.triu_indices_from(c, k=1)]))

    avg_corr = pd.Series(
        [
            _avg_corr(rets.iloc[max(0, i - 60):i])
            for i in range(len(rets))
        ],
        index=rets.index,
    )

    median_spread = spreads.median(axis=1)
    log_median_adv = np.log10(panel.dollar_volume.rolling(20).median().median(axis=1).replace(0, np.nan))

    feat = pd.DataFrame({
        "market_vol": market_vol,
        "avg_corr": avg_corr,
        "spread": median_spread,
        "log_adv": log_median_adv,
    }).dropna()

    if len(feat) < 60:
        # Not enough data to fit — return everything as 'normal'
        labels = pd.Series("normal", index=feat.index)
        probs = pd.DataFrame(0.0, index=feat.index, columns=_REGIME_NAMES)
        probs["normal"] = 1.0
        cents = pd.DataFrame(0.0, index=_REGIME_NAMES, columns=feat.columns)
        return RegimeClassification(
            labels=labels, probabilities=probs, centroids=cents,
            current_regime="normal", current_probabilities={r: 0.0 for r in _REGIME_NAMES},
        )

    Xz, mu, sd = _standardise(feat.values)
    means, variances, weights = _gmm_em(Xz, k=k)
    resp = _gmm_predict(Xz, means, variances, weights)

    # Order by market_vol so 'stressed' is highest
    centroids_orig = means * sd + mu  # back to original units
    order = np.argsort(centroids_orig[:, 0])      # asc by vol
    name_for_idx = {order[0]: "calm", order[1]: "normal", order[2]: "stressed"}
    label_idx = resp.argmax(axis=1)
    labels = pd.Series([name_for_idx[i] for i in label_idx], index=feat.index)
    prob_df = pd.DataFrame(
        resp, index=feat.index,
        columns=[name_for_idx[j] for j in range(k)],
    )[_REGIME_NAMES]

    centroids_df = pd.DataFrame(
        centroids_orig, columns=feat.columns,
        index=[name_for_idx[j] for j in range(k)],
    ).reindex(_REGIME_NAMES)

    return RegimeClassification(
        labels=labels,
        probabilities=prob_df,
        centroids=centroids_df,
        current_regime=labels.iloc[-1],
        current_probabilities=prob_df.iloc[-1].to_dict(),
    )
