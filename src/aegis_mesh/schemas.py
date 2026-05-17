"""Shared data schemas for the detect -> fuse -> decide -> audit chain.

In production these become versioned protobuf/CDR messages on the mesh
(see PLAN.md §3). Python dataclasses here keep the Phase 0 slice runnable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class SensorKind(str, Enum):
    RADAR = "radar"
    PASSIVE_RF = "passive_rf"
    EO_IR = "eo_ir"
    ACOUSTIC = "acoustic"


class ObjectClass(str, Enum):
    UAS = "uas"
    BIRD = "bird"
    AIRCRAFT = "aircraft"
    CLUTTER = "clutter"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Detection:
    """A single sensor return at one timestamp (sensor frame already resolved
    to the common ENU site frame, meters)."""

    t: float
    sensor_id: str
    sensor_kind: SensorKind
    x: float
    y: float
    z: float
    pos_std: float                       # 1-sigma position noise (m)
    rf_linked: Optional[bool] = None     # passive_rf: control link observed
    class_hint: ObjectClass = ObjectClass.UNKNOWN


@dataclass
class Track:
    track_id: int
    t: float
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    pos_cov: float                       # scalar position covariance proxy
    hits: int
    misses: int
    confirmed: bool
    obj_class: ObjectClass = ObjectClass.UNKNOWN
    rf_linked: Optional[bool] = None

    @property
    def speed(self) -> float:
        return (self.vx ** 2 + self.vy ** 2 + self.vz ** 2) ** 0.5


@dataclass
class SwarmObject:
    """A swarm-level threat object — the differentiator over N raw tracks."""

    swarm_id: int
    t: float
    member_track_ids: list[int]
    centroid: tuple[float, float, float]
    n_members: int
    coherence: float                     # 0..1 velocity-alignment of members
    closing_speed: float                 # m/s toward defended asset
    min_time_to_impact: float            # s (inf if not closing)
    threat_level: float                  # 0..1


class EngagementState(str, Enum):
    RECOMMENDED = "recommended"          # human-on-the-loop: awaiting approval
    APPROVED = "approved"
    SUPPRESSED_NO_AUTHORITY = "suppressed_no_authority"


@dataclass
class EngagementOrder:
    t: float
    swarm_id: int
    target_track_id: int
    effector_id: str
    effector_kind: str
    expected_cost: float
    state: EngagementState
    rationale: str


@dataclass
class AuditRecord:
    seq: int
    t: float
    kind: str                            # "decision" | "cycle" | "policy"
    payload: dict
    prev_hash: str
    this_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
