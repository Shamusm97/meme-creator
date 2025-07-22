from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from config.domain.models import ScriptConfig, Character


@dataclass
class Script:
    """Data structure to hold scripe entries"""

    entries: List[ScriptEntry]


@dataclass
class ScriptEntry:
    """Data structure to hold script information"""

    character: Character
    content: str


class LLMClient(ABC):
    @abstractmethod
    def generate_script(self, script_config: ScriptConfig) -> Script:
        NotImplementedError("Subclasses must implement this method")
