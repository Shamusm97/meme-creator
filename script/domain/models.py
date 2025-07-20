from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from config.domain.models import ScriptConfig, Character


@dataclass
class ScriptEntry:
    """Data structure to hold script information with timing data"""

    character: Character
    content: str




class LLMClient(ABC):
    @abstractmethod
    def generate_script(self, script_config: ScriptConfig) -> List[ScriptEntry]:
        NotImplementedError("Subclasses must implement this method")
