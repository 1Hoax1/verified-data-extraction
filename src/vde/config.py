from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Config:
    workspace_root: Path

    @classmethod
    def from_environment(cls):
        return cls(Path(os.environ.get("VDE_WORKSPACE", ".workspace")))
