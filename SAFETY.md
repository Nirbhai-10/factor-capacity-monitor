# SAFETY — Permanent Project Boundary

This boundary is a permanent, non-negotiable constraint on this project. It
applies to every contributor, every branch, every release.

## Scope

This project builds a **defensive** counter-swarm system: detect, track,
classify, decide, and (for authorized state customers only) mitigate hostile
incoming drones.

## Hard prohibitions

1. **No offensive weaponization.** No design, code, or documentation for
   weaponized attack drones, warheads, payloads, or systems intended to harm
   people or infrastructure.
2. **No real-world targeting.** Red-team assets and simulations target only
   our own instrumented range or synthetic entities. Never real
   infrastructure, vehicles, aircraft, or people.
3. **No counter-autonomy attack recipes.** Counter-autonomy work in this repo
   is strictly defensive (defeating an *incoming hostile* drone's guidance)
   and is gated behind verified legal authority. No content that enables
   attacking third-party autonomous systems in the real world.
4. **No detection-evasion or offensive EW guidance** intended to defeat other
   parties' lawful defenses.

## Red-team / simulation rules

- Red-team drones are **non-weaponized** and fly behaviors only.
- Every red-team scenario requires documented legal + range-safety review and
  airspace authorization before any physical flight.
- Red-team and simulation code paths are **fully segregated** from any
  deployable mitigation code path.

## Mitigation authority

Active mitigation (jamming, protocol takeover, kinetic, directed energy) is
restricted to government/military customers with verified legal authority in
their jurisdiction. The default and commercial product is **detect / track /
decide only**. Mitigation features are compiled/configured out of commercial
builds and are gated behind an authority attestation.

## Audit

Every engagement decision is recorded in a tamper-evident, hash-chained audit
log. This is a product requirement and an accreditation requirement.

Violations of this document are project-terminating. If a change appears to
require crossing this boundary, stop and escalate.
