"""Topic pub/sub bus — the in-process stand-in for the Zenoh/DDS mesh
(PLAN.md §2.2/§3). Services publish/subscribe by topic; the engine wires
them together. Decoupled so the real transport swaps in without touching
service logic. Subscribers are isolated: a raising subscriber cannot take
the bus (or another node) down — mirrors mesh fault-isolation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable


class EventBus:
    TOPICS = ("detections", "tracks", "swarms", "orders",
              "metrics", "audit", "frame")

    def __init__(self) -> None:
        self._subs: dict[str, list[Callable]] = defaultdict(list)
        self.dropped = 0

    def subscribe(self, topic: str, fn: Callable) -> None:
        self._subs[topic].append(fn)

    def publish(self, topic: str, msg) -> None:
        for fn in self._subs.get(topic, ()):
            try:
                fn(msg)
            except Exception:
                self.dropped += 1   # fault-isolated: never propagate
