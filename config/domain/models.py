from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ProjectConfig:
    """Configuration for the video project"""

    project_name: str
    character_config: List[Character]
    script_config: ScriptConfig
    tts_config: TTSConfig
    video_config: VideoConfig


@dataclass
class Character:
    """Represents a character with a name and speaking style."""

    name: str
    speaking_style: str = field(default="")
    conversational_role: str = field(default="")
    image_path: Path = field(default=Path(""))
    tts_voice_clone: str = field(default="")
    tts_voice_predefined: str = field(default="")
    tts_voice_profile: str = field(default="")
    tts_voice_profile_overrides: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Character 'name' cannot be empty.")


@dataclass
class TTSConfig:
    """Configuration for text-to-speech settings"""

    base_url: str
    endpoint: str
    timeout: int = field(default=120)
    characters: List[Character] = field(default_factory=list)


@dataclass
class VideoConfig:
    """Configuration for the video generation process"""

    background_video: Path
    characters: List[Character] = field(default_factory=list)


@dataclass
class LLMConfig:
    """Configuration for the LLM client"""

    provider: str
    config: Dict[str, Any]
    api_key: str = field(default="")


@dataclass
class ScriptConfig:
    """
    A dataclass to encapsulate the parameters for generating a multi-speaker dialogue.
    It includes validation and methods to create separate system and user prompt strings.
    """

    system_prompt: str
    user_prompt: str
    overall_conversation_style: str
    main_topic: str
    scenario: str
    dialogue_length: str
    characters: List[Character] = field(default_factory=list)

    def __post_init__(self):
        """
        Performs validation after initialization.
        """
        if not self.overall_conversation_style:
            raise ValueError("Overall conversation style cannot be empty.")
        if not self.main_topic:
            raise ValueError("Main topic cannot be empty.")
        if not self.characters:
            raise ValueError("At least one character must be provided.")
        if not self.dialogue_length:
            raise ValueError("Dialogue length cannot be empty.")

        for char in self.characters:
            if not isinstance(char, Character):
                raise TypeError(
                    "All items in 'characters' must be instances of Character."
                )

    def get_system_prompt(self, extra: str = "") -> str:
        return f"{self.system_prompt}\n{extra}".strip()

    def get_user_prompt(self, extra: str = "") -> str:
        return f"{self.user_prompt}\n{extra}".strip()
