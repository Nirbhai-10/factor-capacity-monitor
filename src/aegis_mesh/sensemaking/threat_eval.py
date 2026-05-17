"""Threat Evaluation (the TE in TEWA).

Roux & van Vuuren; Naeem & Masood — doctrinal air-defence threat
evaluation. Per-track kinematic threat from Closest Point of Approach
(CPA), Time-Before-Hit (TBH), range, speed, classification confidence
and maneuvering state. Feeds the weapon-target assignment (auction).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..schemas import ObjectClass, Track


@dataclass
class ThreatScore:
    track_id: int
    cpa: float            # closest point of approach to asset (m)
    tbh: float            # time before hit / reaching CPA (s, inf if opening)
    rng: float            # current range to asset (m)
    p_uas: float
    score: float          # 0..1


def evaluate(track: Track, asset=(0.0, 0.0, 0.0),
             wez_range: float = 3600.0) -> ThreatScore:
    r = np.array([track.x - asset[0], track.y - asset[1],
                  track.z - asset[2]])
    v = np.array([track.vx, track.vy, track.vz])
    rng = float(np.linalg.norm(r))
    vv = float(v @ v)
    if vv > 1e-6:
        tstar = -float(r @ v) / vv
    else:
        tstar = 0.0
    if tstar <= 0:                     # opening or stationary
        cpa, tbh = rng, math.inf
    else:
        cpa = float(np.linalg.norm(r + v * tstar))
        tbh = tstar
    p_uas = float(track.class_prob.get("uas", 0.0)) if track.class_prob \
        else (1.0 if track.obj_class == ObjectClass.UAS else 0.0)

    # doctrinal sub-scores in [0,1]
    s_cpa = math.exp(-cpa / 400.0)                       # aimed at the asset?
    s_tbh = 0.0 if not math.isfinite(tbh) else \
        max(0.0, 1.0 - tbh / 90.0)                        # imminence
    s_rng = max(0.0, 1.0 - rng / 6000.0)
    s_spd = min(1.0, track.speed / 45.0)
    s_wez = 1.0 if (math.isfinite(tbh) and rng < wez_range) else 0.3
    score = float(np.clip(
        0.30 * s_cpa + 0.25 * s_tbh + 0.15 * s_rng
        + 0.10 * s_spd + 0.20 * p_uas, 0.0, 1.0) * s_wez)
    return ThreatScore(track.track_id, cpa, tbh, rng, p_uas, score)


def evaluate_all(tracks: list[Track], asset=(0.0, 0.0, 0.0)
                 ) -> dict[int, ThreatScore]:
    return {tr.track_id: evaluate(tr, asset) for tr in tracks}
