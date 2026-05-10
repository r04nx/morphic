"""
Action model — represents a remediation action taken on an incident.
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class RemediationAction:
    incident_id: str
    action_type: str          # email | github_pr | runtime_fix
    status: str = "pending"   # pending | running | completed | failed
    details: dict = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    id: Optional[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
