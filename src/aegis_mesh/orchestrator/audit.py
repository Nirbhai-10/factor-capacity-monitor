"""Tamper-evident, hash-chained audit log of every decision (PLAN.md §2.4).

Accreditation + liability requirement. Each record commits to the previous
record's hash, so any retroactive edit breaks the chain.
"""

from __future__ import annotations

import hashlib
import json

from ..schemas import AuditRecord

GENESIS = "0" * 64


def _hash(prev: str, seq: int, t: float, kind: str, payload: dict) -> str:
    blob = json.dumps(
        {"prev": prev, "seq": seq, "t": round(t, 6), "kind": kind,
         "payload": payload},
        sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


class AuditLog:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    @property
    def head(self) -> str:
        return self._records[-1].this_hash if self._records else GENESIS

    @property
    def records(self) -> list[AuditRecord]:
        return list(self._records)

    def append(self, t: float, kind: str, payload: dict) -> AuditRecord:
        seq = len(self._records)
        prev = self.head
        h = _hash(prev, seq, t, kind, payload)
        rec = AuditRecord(seq=seq, t=t, kind=kind, payload=payload,
                          prev_hash=prev, this_hash=h)
        self._records.append(rec)
        return rec

    def verify(self) -> bool:
        prev = GENESIS
        for i, r in enumerate(self._records):
            if r.seq != i or r.prev_hash != prev:
                return False
            if _hash(prev, r.seq, r.t, r.kind, r.payload) != r.this_hash:
                return False
            prev = r.this_hash
        return True
