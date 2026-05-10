"""
Data models for the Morphic Agents module
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class TaskStatus(Enum):
    """Status of agent tasks"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Priority levels for tasks"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentTask:
    """Represents a task to be executed by an agent"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    task_type: str = "general"  # rca, code_review, security, etc.
    project_dir: str = ""
    system_prompt: str = ""
    task_prompt: str = ""
    log_input: Optional[str] = None
    custom_prompt: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    max_retries: int = 3
    timeout: int = 300  # 5 minutes default
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    error: Optional[str] = None
    result: Optional['AgentResult'] = None


@dataclass
class AgentResult:
    """Result from an agent task execution"""
    task_id: str
    success: bool
    data: Dict[str, Any]
    execution_time: float
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)  # File paths, PR URLs, etc.
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
