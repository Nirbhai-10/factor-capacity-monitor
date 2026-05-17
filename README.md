# AEGIS-MESH — Counter-Swarm Defense (autonomy + data OS)

A sensor- and effector-agnostic real-time autonomy + data layer for
counter-swarm defense. The moat is the autonomy/data flywheel, not the
hardware (see `PLAN.md`).

> **Defensive only.** Read `SAFETY.md` first — a permanent, non-negotiable
> project boundary. Red-team and simulation target only our own synthetic
> range; no offensive weaponization.

## Value proposition

A single defeat mechanism does not span the threat. Cheap RF/GNSS
soft-kills are **useless against RF-silent autonomous / fibre-optic
drones** — the contingent that defeats "older framework" defences.
AEGIS-MESH classifies each contact's **autonomy generation**, attempts
the cheapest *effective* tool, and on no-effect **re-classifies and
escalates** (engage-assess-reengage) to counter-autonomy / HPM / laser /
net so nothing leaks.

Quantified (`aegis-capacity`, multi-generation saturation raid, 25 % of
the raid RF-silent autonomous, seed 0):

| Raid | Leakage | Autonomous defeated | Escalations | $/kill | Cost-exchange* |
|--:|--:|--:|--:|--:|--:|
| 25  | 0 % | all | yes | ~$140 | ~17× |
| 100 | 0 % | all | yes | ~$60  | ~17× |
| 200 | 0 % | all (50/50) | 643 | ~$97 | ~21× |

\*attacker $ : our $, attacker drone @ $2,000. **Holds ≥200 drones under
the 5 % leakage ceiling** — see `examples/value_proposition.png`. The
attacker spends ~20× what we do; that is the inversion of the cost curve
the whole programme is about.

## End-to-end system (implemented, runnable, tested)

```
SENSE ───────────► FUSE ──────────► SENSEMAKE ────► DECIDE ───────► EFFECT
multi-site mesh    EKF tracker      DBSCAN swarm    WTA + auth      authority-gated
radar / passiveRF  Cartesian +      intent, hull,   FSM, approval   simulated effect
/ EO-IR / acoustic bearing-only     axis, TTI,      queue, audit    + Pkill model
node-loss inject   KD-tree GNN      mothership      hash-chain      closed-loop
                   classifier
```

### Battle-grade algorithms (from the MTT / air-defence literature)

| Algorithm | Reference | Where |
|---|---|---|
| **GM-PHD** multi-target filter (default tracker) — RFS, no explicit association, robust to clutter/missed/unknown N | Vo & Ma, *IEEE T-SP* 2006 | `fusion/gmphd.py` |
| **IMM** (CV + fixed-rate coordinated-turn bank) for maneuvering targets | Blom & Bar-Shalom, *IEEE TAC* 1988 | `fusion/imm.py` |
| **Chan–Ho** closed-form TDOA + **AOA** triangulation for the passive-RF mesh | Chan & Ho, *IEEE T-SP* 1994 | `fusion/localization.py` |
| **TEWA** threat evaluation (CPA / TBH / WEZ) | Roux & van Vuuren | `sensemaking/threat_eval.py` |
| **Bertsekas auction** (ε-scaling) optimal weapon-target assignment | Bertsekas, LIDS 1987 | `orchestrator/auction.py` |
| **Submodular max-coverage** area-effector burst placement (1−1/e) | — | `orchestrator/wta.py` |
| **OSPA(c,p)** multi-target tracking metric | Schuhmacher, Vo & Vo, *IEEE T-SP* 2008 | `metrics/ospa.py` |
| **Generation-conditioned effectiveness + engage-assess-reengage** (RF/GNSS soft-kill vs. autonomous; escalation) | Ukraine 2024-26 doctrine | `orchestrator/effectiveness.py` |

| Vertical | What's actually coded |
|---|---|
| **sim** | 7-site sensor mesh: radar (RCS/range Pd + clutter), passive-RF **bearing-only**, EO-IR, acoustic; signature targets; mothership child-release; node-loss injection |
| **fusion** | **GM-PHD** filter (default) + GNN-EKF; **IMM**; multilateration; KD-tree gating (scales to 1000+); persistent-label manager; trained softmax **classifier** |
| **sensemaking** | **DBSCAN** swarm clustering + convex hull + axis/coherence/TTI; **TEWA** per-track threat; lone-wolf handling |
| **orchestrator** | **auction** point WTA + submodular area bursts; Pkill model; keep-out; engagement-authority **FSM** + human-on-the-loop queue; hash-chained **audit** |
| **mesh** | decentralised pub/sub bus with fault isolation |
| **server** | FastAPI: live COP **WebSocket**, approve/deny, `/healthz`, `/metrics` (Prometheus), `/api/replay` |
| **web / web-app** | zero-build live ops dashboard + **Vercel-deployable replay dashboard** (timeline scrubber, KPI bar, layers) |
| **infra** | `Dockerfile`, `docker-compose.yml`, env config, deterministic replay export |
| **viz** | offline matplotlib COP renderer → PNG + animated GIF |

## Quickstart

```bash
pip install -e ".[dev]"
pytest -q                                  # 29 regression tests (incl. algos)
aegis-sim all                              # Threat Library + metrics
aegis-sim mixed_dark_saturation --kill-site radar-N@12   # resilience
aegis-sim single_drone --no-mitigation     # commercial detect/track build
aegis-serve                                # live COP :8000  (/healthz /metrics)
aegis-render mixed_dark_saturation         # PNG + GIF in examples/
aegis-sim layered_raid                     # multi-generation raid + escalation
aegis-capacity                             # value-proposition chart + JSON
aegis-export                               # build replay JSON for the dashboard
docker compose up --build                  # containerised stack
# operators tune doctrine/default.yaml (ROE, effectors, attacker economics)
```

### Deploy the dashboard to Vercel (hosted link)

```bash
aegis-export                 # writes web-app/public/replays/*.json
cd web-app && vercel deploy --prod
```

`web-app/` is a zero-build static COP that plays the bundled deterministic
replays — it runs fully on Vercel with no backend. Point it at a live
backend instead with `?ws=wss://<host>/ws`.

## Validated results (deterministic, seed 0)

GM-PHD tracker, deterministic (seed 0):

| Scenario | Threats | Neut. | Auto defeated | Escal. | Leak | Recall | OSPA | $/kill |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| single_drone | 1 | 1 | 0/0 | 0 | 0 | 100% | ~10 m | $54 |
| coordinated_formation | 8 | 8 | 0/0 | 0 | 0 | 100% | — | $52 |
| mixed_dark_saturation | 30 | 30 | 10/10 | 12 | 0 | 100% | ~29 m | ~$43 |
| **layered_raid** (40% autonomous) | **82** | **81** | **36/36** | **84** | **0** | 100% | ~46 m | ~$141 |
| mothership_release | 11 | 11 | 11/11 | yes | 0 | 100% | — | ~$550 |
| thousand_swarm (multi-gen) | 1000 | ~900 | all | yes | 0 | 100% | — | ~$70 |

The **layered_raid** row is the headline: 36 RF-silent autonomous drones
that the cheap soft-kills cannot touch are still defeated, via 84
engage-assess escalations to the newer framework, at zero leakage. The
GNN-EKF tracker (`--tracker gnn`) trades GM-PHD's RFS rigour for ~10×
speed at extreme scale. `examples/` holds rendered COP snapshots,
animations and the value-proposition chart.

## Layout

```
src/aegis_mesh/{sim,fusion,sensemaking,orchestrator,mesh}/   core verticals
src/aegis_mesh/{engine,pipeline,cli}.py                      closed loop
src/aegis_mesh/server/  web/                                 live COP
src/aegis_mesh/viz/     examples/                            offline render
tests/                                                       23 tests
legacy/factor-capacity-monitor/                              archived prior project
```

`PLAN.md` is the strategy/architecture source of truth; production migrates
the real-time path to Rust/C++ + ROS 2/DDS per `PLAN.md` §3.
