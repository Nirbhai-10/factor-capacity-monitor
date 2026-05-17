"""Defeat-mechanism effectiveness conditioned on drone autonomy generation.

Operational reality (Ukraine 2024-26; Western procurement): fibre-optic /
SATCOM / SLAM-autonomous drones carry no exploitable RF link and ignore
GNSS, so RF jamming, GNSS spoofing and RF-cyber take-over — the cheap
"older framework" soft-kills — are INEFFECTIVE against them. No single
defeat mechanism spans the threat spectrum; the layered framework must
match the cheapest *effective* tool to each generation and escalate when
a soft-kill has no effect.

`base_pkill[effector_kind][guidance]` is the conditional kill probability
(0 => mechanism does not work on that generation).
"""

from __future__ import annotations

from ..schemas import GuidanceClass as G

# effector_kind -> {GuidanceClass: base Pkill}
BASE_PKILL: dict[str, dict[G, float]] = {
    # --- soft-kill (cheap, "older framework") -------------------------------
    "soft_kill_cyber": {G.RF_REMOTE: 0.95, G.GNSS_AIDED: 0.55,
                        G.AUTONOMOUS: 0.0, G.UNKNOWN: 0.5},
    "gnss_spoof":      {G.RF_REMOTE: 0.45, G.GNSS_AIDED: 0.90,
                        G.AUTONOMOUS: 0.0, G.UNKNOWN: 0.4},
    # --- counter-autonomy (the "newer framework" soft option) --------------
    "optical_dazzle":  {G.RF_REMOTE: 0.20, G.GNSS_AIDED: 0.25,
                        G.AUTONOMOUS: 0.55, G.UNKNOWN: 0.35},
    # --- hard / generation-agnostic ----------------------------------------
    "hpm":             {G.RF_REMOTE: 0.92, G.GNSS_AIDED: 0.90,
                        G.AUTONOMOUS: 0.85, G.UNKNOWN: 0.88},
    "laser":           {G.RF_REMOTE: 0.80, G.GNSS_AIDED: 0.80,
                        G.AUTONOMOUS: 0.78, G.UNKNOWN: 0.79},
    "net_interceptor": {G.RF_REMOTE: 0.88, G.GNSS_AIDED: 0.88,
                        G.AUTONOMOUS: 0.86, G.UNKNOWN: 0.87},
}


def base_pkill(kind: str, guidance: G) -> float:
    return BASE_PKILL.get(kind, {}).get(guidance, 0.6)


def expected_pkill(kind: str, guidance_prob: dict[str, float]) -> float:
    """Pkill marginalised over the *estimated* guidance distribution —
    what the planner uses before the true generation is confirmed."""
    tbl = BASE_PKILL.get(kind)
    if not tbl:
        return 0.6
    if not guidance_prob:
        # unknown generation: assume the harder (autonomous-heavy) prior
        return 0.5 * tbl[G.AUTONOMOUS] + 0.3 * tbl[G.GNSS_AIDED] \
            + 0.2 * tbl[G.RF_REMOTE]
    s = 0.0
    for g, p in guidance_prob.items():
        s += p * tbl.get(G(g), 0.6)
    return s


def is_soft_kill(kind: str) -> bool:
    return kind in ("soft_kill_cyber", "gnss_spoof")
