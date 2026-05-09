"""
Trace model — represents a log event in the timeline of an incident.
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class TraceEvent:
    incident_id: str
    timestamp: str
    service: str
    log_level: str = "INFO"
    message: str = ""
    endpoint: str = ""
    async_orphan: bool = False
    raw_log: dict = None

    def __post_init__(self):
        if self.raw_log is None:
            self.raw_log = {}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
