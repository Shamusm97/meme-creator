from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List
from config.domain.models import LLMConfig, ScriptConfig


@dataclass
class ScriptEntry:
    """Data structure to hold script information with timing data"""

    character: str
    dialogue: str


class LLMClient(ABC):
    @abstractmethod
    def generate_script(self, script_config: ScriptConfig) -> List[ScriptEntry]:
        NotImplementedError("Subclasses must implement this method")
