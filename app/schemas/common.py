from datetime import datetime
from typing import Dict, List, Optional, Any, Literal

from pydantic import BaseModel, Field


class CodeFile(BaseModel):
    """Model representing a file in a code snapshot."""
    path: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class CodeSnapshot(BaseModel):
    """Model for a code snapshot, which contains multiple files."""
    id: str
    timestamp: datetime
    files: Dict[str, CodeFile]
    metadata: Optional[Dict[str, Any]] = None


class DiffResult(BaseModel):
    """Model for the result of comparing two code snapshots."""
    added: Dict[str, CodeFile]
    modified: Dict[str, CodeFile]
    deleted: List[str]


class ContainerConfig(BaseModel):
    """Configuration for a Docker container."""
    env: Dict[str, str] = Field(default_factory=dict)
    volumes: List[Dict[str, str]] = Field(default_factory=list)
    network_mode: str = "bridge"
    memory: int = 512  # MB
    cpu_shares: int = 1024


class DockerContainer(BaseModel):
    """Model representing a Docker container."""
    id: str
    status: Literal["creating", "running", "paused", "exited", "destroyed"]
    start_time: datetime
    image: str
    config: ContainerConfig
