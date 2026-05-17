# Counter-Swarm Defense Stack — End-to-End Build Plan

## Context

The cost curve of aerial attack has inverted. A $500 FPV or a coordinated swarm of
a thousand $1–5k autonomous drones can threaten assets defended by $3M interceptors.
The defensive market is real and accelerating: global C-UAS ~$6.6B (2025) → ~$20B+
(2030) at ~25% CAGR; US DoD has made counter-small-UAS a stated budget priority
(Replicator 2, JIATF-401, the $1B "Drone Dominance" / Blue List motion); FIFA 2026
is a near-term civil catalyst; India's DRDO D4 / SAKSHAM grid and the Operation
Sindoor combat results have created a hard, proven domestic demand signal and an
export pull (Taiwan already requesting D4).

The strategic insight driving this plan: **counter-swarm defense is becoming a
real-time distributed-systems problem, not a weapons problem.** The winner looks
more like Cloudflare/Palantir than Raytheon — a sensor-and-effector-agnostic
autonomy + data layer that gets better with every engagement, with hardware as a
deliberate, modular complement rather than the moat itself.

**Build base:** India. **Market:** global. This is a deliberate advantage:
ITAR-free supply chain, ~10x cost advantage on engineering and hardware, a live
combat-proven home market (DRDO/iDEX/ADITI pathways), 5% GST / military-grade
tax-exempt drone policy, and the ability to sell to Gulf, SE Asia, Africa,
Latin America, Taiwan, Eastern Europe and other non-aligned/allied buyers that
US ITAR-bound vendors cannot serve quickly.

**Scope decision (confirmed with user):** We build the full stack end-to-end.
The "attack point of view" is strictly **defensive validation**: physical,
**non-weaponized** threat-representative red-team swarm drones + a high-fidelity
adversary simulation, used only on our own closed range to certify our defenses.
This plan contains **no** offensive weaponization, no targeting of real
infrastructure/people, and no counter-autonomy "attack recipes" intended to
enable real-world attacks. All counter-autonomy work below is defensive
(defeating an incoming hostile drone's navigation) and gated behind legal
authority. This boundary is a permanent constraint on the project.

---

## 1. Product Thesis & The Moat

We are building **"the autonomy + data OS for counter-swarm defense"** —
codename internally **AEGIS-MESH** (placeholder).

Four compounding moats, in priority order:

1. **Data flywheel (primary moat).** Every detection, track, classification,
   engagement and outcome — from our own range, from sim, and from deployed
   sites — feeds a labeled multi-modal dataset (RF spectra, radar tracks,
   EO/IR imagery, acoustic signatures, swarm behaviors, engagement outcomes).
   This trains classifiers and weapon-target-assignment policies that no
   single-sensor or hardware vendor can match. The red-team range + sim is what
   makes this flywheel turn on day one, before deployments exist. **This is why
   we control our own threat range.**
2. **Sensor/effector-agnostic integration layer.** Open SDK; ingest any
   radar/RF/EO-IR/acoustic; task any effector (nets, HPM-class, EW/cyber-takeover,
   laser, kinetic interceptor, gun mounts). We integrate the messy pile rather
   than replace it — initially complementary to Anduril Lattice / Fortem SkyDome
   / DRDO D4 rather than competing head-on.
3. **Cost structure.** India engineering + ITAR-free BOM → demonstrably low
   cost-per-kill and low platform cost vs. Western primes; this is a sales weapon
   and a margin moat.
4. **Accreditation & program lock-in.** Once embedded in a program of record
   (iDEX/Make-II in India; allied MoDs; eventually US via a US subsidiary +
   partner), the procurement bureaucracy becomes our moat against new entrants.

Business model: software subscription/site (recurring) + autonomy compute
appliance + optional effector hardware margin + a "threat library + sim" data
product. The recurring software/data line is the equity-value driver.

---

## 2. End-to-End System Architecture

Layered, mesh-native, edge-first. Every layer designed to degrade gracefully
under jamming, GPS denial, and node loss (the system itself must be a resilient
distributed system).

```
[ SENSE ] → [ EDGE COMPUTE + MESH ] → [ FUSE / SENSEMAKE ] → [ DECIDE / ORCHESTRATE ] → [ EFFECT ]
   |              |                         |                        |                      |
 radar         Jetson Orin /            multi-target track       weapon-target          nets / entangle
 passive RF    x86 GPU appliance        fusion, MHT/JPDA,        assignment, swarm      HPM-class effector
 EO/IR         DDS/Zenoh mesh           ML classification,       deconfliction,         defensive EW /
 acoustic      ATAK/edge UI             intent & swarm-intent    engagement-authority   protocol takeover
 ADS-B/Remote-ID                        estimation               policy (human-on-loop) laser / kinetic
```

### 2.1 Sensing layer (open, multi-modal, redundant)
- **Radar:** electronically-scanned (metamaterial/AESA-class, e.g. Echodyne-class
  or Indian AESA from BEL/data-partner) for low-RCS Group 1–3 tracking; doppler
  micro-classification (rotor vs. bird).
- **Passive RF (primary for swarm early-warn):** wideband SDR sensing of control
  links, video downlinks, telemetry, Remote-ID; geolocation by TDOA/AoA across
  mesh nodes. Critical because it is passive, networkable, cheap, and scales to
  swarms. Hardware: Ettus/USRP-class + custom RF front-ends; later ASIC/SoC.
- **EO/IR:** gimballed day/thermal cameras for visual ID, fiber-optic / dark-drone
  detection (the threats RF can't see), and battle-damage assessment.
- **Acoustic arrays:** cheap last-line for low/slow/dark drones; mesh-distributed.
- **Cooperative:** ADS-B, Remote-ID, local UTM feeds for friend/clutter rejection.
- Design rule: **no single sensor is load-bearing.** Fiber-optic/autonomous
  drones defeat RF; HPM/EO/IR/acoustic cover that gap. Swarms defeat single-FOV
  sensors; mesh many cheap nodes for 360° persistent coverage.

### 2.2 Edge compute + mesh networking (the "distributed system" core)
- **Edge nodes:** NVIDIA Jetson Orin (AGX/NX) for sensor-adjacent inference
  (YOLO-class detection/track at the sensor, ~real-time), plus a ruggedized
  x86+GPU "fusion appliance" per site (analogous to Anduril Menace-T concept).
- **Mesh data plane:** decentralized pub/sub over **DDS (RTI / eProsima Fast-DDS)**
  and/or **Eclipse Zenoh** for low-bandwidth, lossy, contested links; MANET radios
  (Silvus-class / Indian equivalents) for the RF transport. No single point of
  failure; any node can host fusion; orders route peer-to-peer.
- **Resilience:** store-and-forward, CRDT-based shared world model, autonomous
  fallback engagement rules if the human link drops (within pre-authorized ROE).

### 2.3 Fusion & sensemaking
- **Track fusion:** multi-hypothesis tracking (MHT) / JPDA / labeled multi-Bernoulli
  across heterogeneous sensors → single de-duplicated air picture; out-of-sequence
  measurement handling; mesh-distributed track stitching.
- **Classification:** multi-modal ML (RF-spectrogram CNN/transformer + EO/IR
  vision + radar micro-doppler + acoustic) → UAS / bird / aircraft / clutter,
  type/model, and **payload/threat estimation**.
- **Swarm-intent estimation:** the differentiator. Graph/temporal models over
  many tracks to detect coordinated behavior, formation, mothership-child
  patterns, axis-of-attack, and time-to-impact — outputting *swarm-level* threat
  objects, not just N independent tracks.

### 2.4 Decide / orchestrate (the autonomy brain)
- **Weapon-Target Assignment (WTA):** real-time combinatorial optimization /
  RL-assisted policy assigning the cheapest sufficient effector to each threat,
  maximizing leakage-prevention under magazine/energy/keep-out constraints
  (this is the "cost-per-kill" engine and a core IP asset).
- **Engagement-authority state machine:** strict **human-on-the-loop** by
  default; pre-authorized auto-engage envelopes only where law/ROE permit;
  full audit log of every decision (accreditation + liability requirement).
- **Effector deconfliction:** keep-out zones, fratricide avoidance, airspace
  (UTM) and friendly-asset deconfliction, collateral-damage estimation.
- **Swarm-vs-swarm orchestration:** coordinate our own defensive interceptor
  drones as a cooperative team (assignment, pursuit, re-tasking) — a distributed
  multi-agent control problem.

### 2.5 Effector layer (modular, layered, "shots cheaper than threats")
Defense-in-depth, cheapest-effective-first:
- **Soft / non-kinetic, scalable:** defensive RF/GNSS denial & **protocol/cyber
  takeover** (force-land hostile drone) — legal-authority-gated; **HPM-class
  wide-effect** counter-electronics for dense swarms (the "one burst, dozens
  down" layer — integrate partner HPM e.g. Epirus-class / DRDO DEW, then build
  IP over time).
- **Mid layer — physical capture:** autonomous **net/entanglement interceptor**
  drone (recoverable, low collateral, safe over sensitive sites; multi-net
  magazine; drone-on-drone autonomy) — our owned hardware differentiator.
- **Hard layer:** laser (integrate DEW partners / DRDO laser) and low-cost
  kinetic interceptor / smart gun-mount for the residual.
- We **own the C2/autonomy and the net-interceptor**; we **integrate** HPM/laser
  via the open SDK initially, building proprietary effector IP only where the
  data/autonomy moat is strongest.

### 2.6 C2 / operator experience
- ATAK/WinTAK plugin + standalone web/3D common operating picture; one-screen
  swarm picture (not 1000 windows); recommended actions with human approval;
  after-action replay (feeds the data flywheel and customer trust).
- Standards: integrate to FAAD-C2 / allied C2 and Lattice-style meshes via
  adapters so we slot into existing buyers rather than rip-and-replace.

---

## 3. Exact Software Stack & Infrastructure

**Edge / real-time (on the appliance & drones)**
- Core real-time services: **Rust** (safety-critical fusion, WTA, mesh) +
  **C++** where ecosystem demands (DDS, CUDA, ROS 2 nodes).
- Robotics/autonomy on interceptor drones: **ROS 2 (Jazzy/Rolling) + DDS**,
  PX4/ArduPilot flight stack, MAVLink; **NVIDIA Isaac ROS** + TensorRT for
  GPU-accelerated perception on Jetson Orin.
- Inference: TensorRT / ONNX Runtime; YOLO-class detectors, RF
  CNN/transformer classifiers, micro-doppler nets.
- Middleware/mesh: **Eclipse Zenoh** + **Fast-DDS/RTI DDS**; protobuf/CDR
  schemas; CRDT world model.

**Cloud / back-of-house (training, fleet, data product)**
- **Kubernetes** (managed; India region + sovereign/on-prem option per customer)
  — strict data-residency separation per nation/customer.
- Data lake + feature store; **MLOps**: MLflow/W&B, DVC/LakeFS for dataset
  versioning, Triton inference, Argo/Kubeflow pipelines, automated
  retrain-on-new-engagement-data (the flywheel, operationalized).
- Streaming: Kafka/Redpanda for telemetry ingest; ClickHouse/Timescale for
  track/telemetry analytics; object store for sensor media.
- Observability: OpenTelemetry, Prometheus/Grafana, immutable audit log
  (engagement decisions) with cryptographic signing for accreditation.
- Security: zero-trust, mTLS everywhere, hardware root-of-trust on appliances,
  signed/OTA-updatable models & firmware, full air-gap deployment mode.

**Simulation & digital twin (moat infrastructure — see §4)**
- **NVIDIA Isaac Sim / Omniverse** + **Gazebo/Ignition** for physics & sensor
  models; **AirSim-class** for vision; SITL (PX4/ArduPilot) for flight;
  custom **RF/EW propagation + radar/acoustic simulators**; large-scale
  swarm-behavior simulator (1000+ agents) for adversary modeling and WTA
  policy training; domain randomization + sim-to-real pipeline.

**Repo / engineering**
- Monorepo (Bazel or Nx + Cargo/Colcon workspaces); the current
  `factor-capacity-monitor` content is unrelated and will be archived — we
  scaffold a clean monorepo on the working branch.

---

## 4. Red-Team Range & Simulation (Defensive Validation Only)

This is **moat infrastructure**, not a weapons program. We cannot certify a
counter-swarm system without a representative threat; owning the threat range +
sim is what lets the data flywheel spin before we have customers.

- **Closed instrumented range** (and a high-fidelity sim mirror): non-weaponized
  threat-representative drones flying realistic *behaviors* — EW-resistant /
  autonomous nav, fiber-optic/dark profiles, formations, mothership-child,
  saturation timing, decoys. Purpose: measure detection range, track continuity,
  classification accuracy, leakage rate, and cost-per-kill against progressively
  harder swarms.
- **Adversary simulation:** 1000+-agent swarm sim to develop swarm-intent
  models and WTA policies at scale, then validate on the physical range
  (sim-to-real). All targeting is synthetic / range-only.
- **Hard constraints:** no warheads/payloads, no real-infrastructure or
  personnel targets, range-safety + DGCA/airspace authorization, full
  segregation from any deployed-system code path, legal review of every
  red-team scenario. Documented as a permanent policy in the repo.

The output is a versioned **Threat Library** + benchmark suite — itself a
sellable data product and the basis of customer trust ("here is exactly how it
performs vs. this threat class").

---

## 5. Hardware & BOM (modular, ITAR-free, India-sourced where possible)

- Fusion appliance: rugged x86 + NVIDIA GPU; Jetson Orin sensor pods.
- Passive-RF node: SDR + wideband front-end + GPS-disciplined clock for TDOA;
  designed for low unit cost and dense meshing (swarm coverage economics).
- EO/IR gimbal pod; MEMS/electronically-scanned radar (BEL/partner or imported
  non-ITAR); acoustic array.
- Net/entanglement interceptor drone: carbon airframe, PX4/ArduPilot + our
  autonomy payload (Orin), multi-net launcher, recoverable.
- MANET radios (Indian/non-ITAR), batteries (GST-exempt military-grade), all
  selected for export-friendly (non-ITAR) bill of materials — a deliberate
  sales advantage over Western primes.

---

## 6. Legal, Regulatory & Export

- **India:** develop under DGCA drone framework + iDEX/ADITI/Make-II and
  DRDO/BEL partnership pathways; leverage 5% GST / military tax-exemption;
  align with SAKSHAM/D4 ecosystem as integrator/complement.
- **Mitigation authority is the key global constraint.** Detection is broadly
  legal; *active mitigation* (jamming, takeover, kinetic) is restricted to
  state actors in most jurisdictions (e.g. US: only DoD/DOJ/DHS/DOE under
  10 USC 130i, which sunsets Dec 31 2026 absent reauthorization — H.R.5061).
  → **Product split:** a fully-legal **detect/track/decide** software product
  for commercial/critical-infrastructure buyers worldwide, and a
  **mitigation-enabled** configuration sold only to authorized
  government/military customers.
- **Export:** position ITAR-free as a feature; comply with India's SCOMET /
  defence-export rules; per-country data residency & sovereign deployment;
  US market entered later via a US subsidiary + prime/partner (not the
  beachhead).

---

## 7. Go-To-Market (build India, sell global)

- **Beachhead:** Indian MoD / DRDO-BEL ecosystem via iDEX/ADITI + critical
  infrastructure (airports, refineries, borders) — combat-proven demand, fast
  feedback, reference customers.
- **Wave 2:** allied/non-aligned exports where ITAR-free + cost wins fastest —
  Gulf, SE Asia, Taiwan, Africa, LatAm, Eastern Europe; frontline data
  partnerships (with strict legal/ethics gating) to accelerate the flywheel.
- **Wave 3:** Western critical-infrastructure (detect/track SaaS — FIFA-2026-
  class events, data centers, energy) and US federal via subsidiary + prime
  partnership / Replicator-style motions.
- Funding: Indian iDEX/ADITI grants + defence-tech VC (record 2025–26 flows;
  ~8% of global VC now defense). Milestone-gated raises tied to range
  benchmarks.

---

## 8. Phased Roadmap (each phase ships something testable)

**Phase 0 — Foundations (wks 1–6).** Scaffold clean monorepo; CI; schemas
(tracks, detections, orders, audit); sim skeleton (Gazebo/Isaac + PX4 SITL);
synthetic RF/radar generators; **Threat Library v0** spec + red-team safety
policy doc.

**Phase 1 — Detect/Track core (wks 6–16).** Multi-sensor track fusion
(MHT/JPDA) over simulated + recorded data; passive-RF geolocation prototype;
baseline ML classifier; 3D COP UI; everything mesh-native (DDS/Zenoh) and
node-loss tolerant. Deliverable: software detect/track demo on sim + bench
hardware → first sellable (legal-everywhere) product.

**Phase 2 — Decide (wks 16–28).** Swarm-intent estimation; WTA optimizer;
engagement-authority state machine + audit log; effector adapter SDK; ATAK
plugin; integrate ≥1 real sensor + ≥1 simulated effector. Benchmark vs.
Threat Library on the range/sim.

**Phase 3 — Effect (wks 28–48).** Net/entanglement interceptor autonomy
(drone-on-drone) on real hardware at the range; integrate a partner
HPM/laser/EW effector via SDK; closed-loop detect→decide→effect against
progressively harder red-team swarms; publish benchmark results.

**Phase 4 — Scale & flywheel (ongoing).** Fleet/MLOps retrain loop; sovereign
multi-tenant deployments; data-product packaging; certification/accreditation;
expand effector portfolio where the data moat is strongest.

---

## 9. Critical Files / Initial Implementation (Phase 0–1)

Scaffold on branch `claude/counter-swarm-defense-plan-QdOx1` (archive existing
unrelated repo content):

- `/PLAN.md`, `/SAFETY.md` (permanent offensive-scope boundary + red-team policy)
- `/proto/` — shared schemas (detections, tracks, swarm-objects, orders, audit)
- `/services/fusion/` (Rust) — MHT/JPDA track fusion + mesh world model
- `/services/sensemaking/` (Rust/Python) — classifier + swarm-intent
- `/services/orchestrator/` (Rust) — WTA + engagement-authority FSM + audit log
- `/edge/perception/` (C++/Python, ROS 2 + Isaac) — sensor-edge inference
- `/mesh/` — Zenoh/DDS transport, CRDT world model
- `/sim/` — Gazebo/Isaac worlds, PX4 SITL, RF/radar/acoustic + swarm sim,
  Threat Library scenarios
- `/cop/` — 3D common operating picture (web) + ATAK plugin
- `/mlops/` — dataset versioning, training pipelines, retrain loop
- `/infra/` — k8s, IaC, observability, audit-log signing
- `/redteam/` — sim-only adversary scenarios + safety gates (no weaponization)

## 10. Verification / Test Plan

- **Unit/integration:** deterministic replay of recorded + synthetic sensor
  data; fusion accuracy vs. ground truth; chaos tests for node loss / jamming
  (resilience is a product requirement, so it's a test requirement).
- **Sim end-to-end:** PX4 SITL + Isaac/Gazebo + RF/swarm sim → run the full
  detect→decide→effect loop against Threat Library scenarios; track leakage
  rate, classification F1, decision latency, simulated cost-per-kill as the
  headline regression metrics in CI.
- **Range:** staged live tests vs. non-weaponized red-team swarms of increasing
  difficulty; published benchmark report per release (the customer-trust and
  data-flywheel artifact).
- **Security/accreditation:** audit-log completeness & signature verification,
  air-gap deployment test, model/firmware OTA signing, pen-test.

## 11. Key Risks

- Mitigation-authority/legal limits → mitigated by detect/track-first product
  split.
- Incumbents (Anduril, Epirus, Fortem, DRDO/BEL) → mitigated by integrate-not-
  replace + cost + data moat + ITAR-free reach.
- Hardware capital intensity → software/data-first sequencing; partner
  effectors before owning them.
- Export/dual-use & ethics → strict legal gating, audit-by-design, permanent
  offensive-scope boundary in `SAFETY.md`.
- Sim-to-real gap → owned instrumented range closes it.

## Sources

- [Lockheed Martin — C-UAS swarm defense](https://www.lockheedmartin.com/en-us/news/features/2025/the-counter-uas-challenge-closing-the-gap-in-drone-swarm-defense.html)
- [Breaking Defense — mobile C-UAS architecture](https://breakingdefense.com/2025/10/defending-against-the-swarm-with-a-mobile-counter-uas-architecture/)
- [Modern War Institute — frontline fusion network architecture](https://mwi.westpoint.edu/frontline-fusion-the-network-architecture-needed-to-counter-drones/)
- [Anduril Lattice — Command & Control](https://www.anduril.com/lattice/command-and-control)
- [Anduril Lattice Mesh](https://www.anduril.com/lattice/lattice-mesh)
- [Anduril Lattice SDK](https://www.anduril.com/lattice/lattice-sdk)
- [DefenseScoop — Army $20B Anduril contract](https://defensescoop.com/2026/03/14/anduril-20-billion-dollar-army-contract/)
- [Epirus Leonidas — HPM cUAS](https://www.epirusinc.com/electronic-warfare)
- [Epirus — HPM defeats fiber-optic UAS](https://www.epirusinc.com/press-releases/epirus-leonidas-demonstrates-successful-use-of-high-power-microwave-to-defeat-fiber-optic-controlled-uas)
- [DroneLife — Leonidas one burst dozens down](https://dronelife.com/2025/10/15/microwave-counter-drone-system/)
- [Allen Control Systems Bullfrog defeats swarm](https://www.unmannedairspace.info/counter-uas-systems-and-policies/allen-control-systems-bullfrog-defeats-drone-swarm-during-us-army-test/)
- [Global Counter-UAS Interceptor Market](https://www.prnewswire.com/news-releases/global-counter-uas-interceptor-market-surges-amid-escalating-drone-warfare-threats-302732869.html)
- [IEEE Spectrum — autonomous drone warfare](https://spectrum.ieee.org/autonomous-drone-warfare)
- [IEEE Spectrum — Ukraine killer drones defeat EW](https://spectrum.ieee.org/ukraine-killer-drones)
- [Defense Advancement — countering fiber-optic drones](https://www.defenseadvancement.com/feature/evolving-countermeasures-for-the-rise-of-fiber-controlled-drones/)
- [10 U.S. Code § 130i (LII)](https://www.law.cornell.edu/uscode/text/10/130i)
- [H.R.5061 — Counter-UAS Authority Reauthorization Act](https://www.congress.gov/bill/119th-congress/house-bill/5061/text)
- [FAA Interagency Legal Advisory on UAS Detection & Mitigation](https://www.faa.gov/sites/faa.gov/files/uas/resources/c_uas/Interagency_Legal_Advisory_on_UAS_Detection_and_Mitigation_Technologies.pdf)
- [CRS — FY2025 NDAA Countering UAS](https://www.everycrsreport.com/files/2025-02-03_IN12418_5590e51a8cd50a67f90c97d1dceea8fb1b498768.html)
- [CRS — DOD Replicator Initiative](https://www.congress.gov/crs-product/IF12611)
- [USNI — Replicator report to Congress](https://news.usni.org/2025/08/26/report-to-congress-on-defense-departments-replicator-initiative)
- [DRONELIFE — JIATF first Replicator 2 (DroneHunter)](https://dronelife.com/2026/01/14/jiatf-awards-first-replicator-2-contract-for-c-uas-system/)
- [Fortem DroneHunter F700](https://fortemtech.com/products/dronehunter-f700/)
- [Fortem SkyDome neutralizes swarm](https://fortemtech.com/press-releases/2026-02-04-fortem-s-ai-powered-skydome-neutralizes-drone-swarm-with-zero-collateral-damage/)
- [Raytheon Coyote C-UAS](https://www.rtx.com/raytheon/what-we-do/integrated-air-and-missile-defense/coyote)
- [Anduril Roadrunner](https://defensescoop.com/2023/12/01/anduril-develops-new-roadrunner-drones-that-it-says-can-perform-air-defense-missions/)
- [BlueHalo LOCUST Laser Weapon System](https://bluehalo.com/c-uas-autonomous-systems/c-uas-directed-energy/)
- [Army Recognition — DE M-SHORAD first operational use](https://www.armyrecognition.com/news/army-news/2025/exclusive-first-operational-use-for-u-s-army-laser-weapons-with-de-m-shorad-air-defense-vehicle)
- [NVIDIA Jetson / Isaac ROS practical guide](https://thomasthelliez.com/blog/isaac-ros-on-nvidia-jetson-orin-nano-super/)
- [arXiv — ROS2 perception drone sim framework](https://arxiv.org/html/2602.07264v1)
- [ADLINK — ROS 2 + DDS defense](https://www.adlinktech.com/en/ROS2-Solution.aspx)
- [a16z — DoD contracting for startups](https://a16z.com/dod-contracting-for-startups-101/)
- [a16z — American Dynamism 50](https://a16z.com/american-dynamism-50-2025/)
- [Defense News — defense-tech best funding year ever](https://www.defensenews.com/industry/2026/01/20/defense-tech-startups-had-their-best-funding-year-ever-in-2025/)
- [The Defense Post — India $32.5M Zen Technologies anti-drone](https://thedefensepost.com/2025/11/04/india-anti-drone-upgrade/)
- [IDRW — DRDO D4 counter-drone system](https://idrw.org/drdos-d4-counter-drone-system-set-to-safeguard-urban-india-from-rogue-uav-threats/)
- [Organiser — India drone-swarm shield / Operation Sindoor](https://organiser.org/2026/05/15/353580/bharat/from-operation-sindoor-to-ai-warfare-how-india-is-building-a-drone-swarm-shield-across-two-fronts/)
- [IDRW — Taiwan requests India D4](https://idrw.org/taiwan-seeks-indias-battle-proven-d4-anti-drone-system-to-counter-chinese-threats/)
