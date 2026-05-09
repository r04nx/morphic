"""
Incident model — plain dataclass for type-checked passing between agents.
Not an ORM model; PostgreSQL is managed directly via psycopg2.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from datetime import datetime


@dataclass
class Incident:
    trace_id: str
    timestamp: str
    service: str
    level: str = "INFO"
    message: str = ""
    exception: str = ""
    endpoint: str = ""
    order_id: Optional[str] = None
    user_id: Optional[str] = None
    async_orphan: bool = False
    incident_id: Optional[str] = None
    status: str = "active"
    triage_classification: Optional[str] = None
    triage_blast_radius: Optional[str] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Incident":
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in fields})
