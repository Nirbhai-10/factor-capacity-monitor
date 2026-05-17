"""Shared data schemas for the detect -> fuse -> sensemake -> decide -> audit
chain. In production these become versioned protobuf/CDR messages on the
mesh (PLAN.md §3); dataclasses keep the reference engine runnable.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class SensorKind(str, Enum):
    RADAR = "radar"
    PASSIVE_RF = "passive_rf"
    EO_IR = "eo_ir"
    ACOUSTIC = "acoustic"


class MeasKind(str, Enum):
    CARTESIAN = "cartesian"      # x,y,z with isotropic-ish noise
    BEARING = "bearing"          # az,el from a site, no range (passive RF)


class ObjectClass(str, Enum):
    UAS = "uas"
    BIRD = "bird"
    AIRCRAFT = "aircraft"
    CLUTTER = "clutter"
    UNKNOWN = "unknown"


class GuidanceClass(str, Enum):
    """Drone autonomy generation — determines which defeat mechanisms work.

    RF_REMOTE  (Gen-1): manual RF link, GNSS-dependent. Defeated by RF
               jam / GNSS spoof / RF-cyber take-over (cheap soft-kill).
    GNSS_AIDED (Gen-2): RF + autonomous waypoints but GNSS-reliant. GNSS
               spoof effective; RF jam only partial.
    AUTONOMOUS (Gen-3): RF-silent / fibre-optic / SATCOM, visual-inertial
               or SLAM nav, GNSS-independent. RF/GNSS EW is INEFFECTIVE —
               requires HPM / laser / net / kinetic or counter-autonomy
               (optical) defeat. This is the threat older frameworks miss.
    """

    RF_REMOTE = "rf_remote"
    GNSS_AIDED = "gnss_aided"
    AUTONOMOUS = "autonomous"
    UNKNOWN = "unknown"


class TrackStatus(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    COASTING = "coasting"        # confirmed but currently unobserved
    DELETED = "deleted"


class EngagementState(str, Enum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"   # human-on-the-loop queue
    APPROVED = "approved"
    EXECUTING = "executing"
    NEUTRALIZED = "neutralized"
    MISSED = "missed"
    ABORTED = "aborted"
    SUPPRESSED_NO_AUTHORITY = "suppressed_no_authority"  # commercial build


# --------------------------------------------------------------------------- #
# Sensing
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Detection:
    t: float
    sensor_id: str
    sensor_kind: SensorKind
    meas_kind: MeasKind
    site: tuple[float, float, float]          # sensor location, ENU m
    # CARTESIAN payload
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    pos_std: float = 0.0
    # BEARING payload (radians, from `site`)
    az: float = 0.0
    el: float = 0.0
    ang_std: float = 0.0
    # features (used by the classifier)
    rf_linked: Optional[bool] = None
    micro_doppler: float = 0.0                # rotor-blade modulation proxy
    rcs: float = 0.0                          # radar cross-section proxy m^2
    class_hint: ObjectClass = ObjectClass.UNKNOWN


# --------------------------------------------------------------------------- #
# Fusion output
# --------------------------------------------------------------------------- #
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
    pos_cov: float
    hits: int
    misses: int
    status: TrackStatus
    score: float = 0.0
    obj_class: ObjectClass = ObjectClass.UNKNOWN
    class_prob: dict[str, float] = field(default_factory=dict)
    rf_linked: Optional[bool] = None
    rcs: float = 0.0
    micro_doppler: float = 0.0
    guidance: "GuidanceClass" = GuidanceClass.UNKNOWN
    guidance_prob: dict[str, float] = field(default_factory=dict)

    @property
    def confirmed(self) -> bool:
        return self.status in (TrackStatus.CONFIRMED, TrackStatus.COASTING)

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2 + self.vz ** 2)


# --------------------------------------------------------------------------- #
# Sensemaking output
# --------------------------------------------------------------------------- #
@dataclass
class SwarmObject:
    swarm_id: int
    t: float
    member_track_ids: list[int]
    centroid: tuple[float, float, float]
    hull_xy: list[tuple[float, float]]        # convex hull for display
    n_members: int
    coherence: float                          # 0..1 heading alignment
    formation_tightness: float                # 0..1 (1 = very tight)
    axis_of_attack: tuple[float, float]       # unit vector in xy
    closing_speed: float                      # m/s toward asset
    min_time_to_impact: float
    median_time_to_impact: float
    has_mothership: bool
    class_confidence: float                   # mean P(UAS) of members
    threat_level: float                       # 0..1


# --------------------------------------------------------------------------- #
# Decision
# --------------------------------------------------------------------------- #
@dataclass
class EngagementOrder:
    order_id: int
    t: float
    swarm_id: int
    target_track_id: int
    effector_id: str
    effector_kind: str
    pkill: float
    expected_cost: float
    state: EngagementState
    rationale: str
    intercept_xy: tuple[float, float] = (0.0, 0.0)


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #
@dataclass
class AuditRecord:
    seq: int
    t: float
    kind: str
    payload: dict
    prev_hash: str
    this_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def jsonable(obj):
    """Recursively convert dataclasses/enums/tuples to JSON-safe structures."""
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, float):
        return round(obj, 4)
    return obj
