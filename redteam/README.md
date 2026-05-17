# Red-Team — Defensive Validation Only

This directory exists to **validate our own defenses**. It is governed by
`../SAFETY.md`, which overrides anything here.

## Rules

1. Red-team assets are **non-weaponized**. They model adversary *behaviors*
   (ingress profiles, formations, EW-resistant/dark navigation, saturation
   timing) so we can measure detection range, track continuity,
   classification, leakage and cost-per-kill.
2. Targets are **only** our own synthetic simulation or our own closed,
   authorized instrumented range. Never real infrastructure, aircraft,
   vehicles, or people.
3. Red-team / simulation code is **segregated** from any deployable
   mitigation path. Nothing here issues real-world effects.
4. Every physical red-team scenario requires documented legal + range-safety
   review and airspace authorization before any flight.

## Current state

Phase 0 uses the synthetic Threat Library in
`src/aegis_mesh/sim/scenarios.py` only. No physical red-team assets exist.
Physical range work is a later phase and is gated on the reviews above.
