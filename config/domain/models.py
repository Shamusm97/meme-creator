from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class ProjectConfig:
    """Configuration for the video project"""

    project_name: str
    base_output_dir: Path
    character_config: Optional[List[Character]]
    script_config: Optional[ScriptConfig]
    tts_config: Optional[TTSConfig]
    video_config: Optional[VideoConfig]

    def __post_init__(self):
        if not isinstance(self.project_name, str) or not self.project_name.strip():
            raise ValueError("Project name must be a non-empty string")
        self.project_name = self.project_name.strip().replace(" ", "_")


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
    tts_voice_profile_overrides: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Character 'name' cannot be empty.")


@dataclass
class TTSConfig:
    """Configuration for text-to-speech settings"""

    provider: str
    config: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("Provider must be a non-empty string")
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a dictionary")


@dataclass
class VideoConfig:
    """Configuration for the video generation process"""

    provider: str
    background_video: Path
    config: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("Provider must be a non-empty string")
        if not self.background_video or not Path(self.background_video).exists():
            raise ValueError(
                f"Background video file does not exist: {self.background_video}"
            )
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a dictionary")


@dataclass
class LLMConfig:
    """Configuration for the LLM client"""

    provider: str
    config: dict = field(default_factory=dict)
    api_key: str = field(default="")

    def __post_init__(self):
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("Provider must be a non-empty string")
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a dictionary")


@dataclass
class ScriptConfig:
    """
    A dataclass to encapsulate the parameters for generating a multi-speaker dialogue.
    It includes validation and methods to create separate system and user prompt strings.
    """

    overall_conversation_style: str
    main_topic: str
    scenario: str
    dialogue_length: str
    llm_config: LLMConfig
    characters: List[Character] = field(default_factory=list)
    system_prompt_extra: str = field(default="")
    system_prompt_override: str = field(default="")
    user_prompt_extra: str = field(default="")
    user_prompt_override: str = field(default="")

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

    @property
    def system_prompt(self) -> str:
        """
        Generates the static system prompt for the dialogue writer's role and rules.
        """
        if self.system_prompt_override:
            return self.system_prompt_override

        base_system_prompt = (
            "You are a dialogue writer specializing in generating realistic and engaging multi-speaker conversations. "
            "Your primary goal is to produce a clean transcript suitable for text-to-speech conversion, "
            "where each speaker's line is clearly identified.\n\n"
            "Dialogue Requirements:\n"
            '1. Each speaker\'s line MUST be prefixed with their NAME followed immediately by a colon (e.g., "CHARACTER_NAME:"). Do not include any spaces between the name and the colon.\n'
            "2. Do NOT include any narrative descriptions, action tags (e.g., laughs, sighs), or stage directions within the dialogue itself. Only the speaker's name and their spoken words should appear.\n"
            "3. Ensure the dialogue maintains the specified overall conversation style and the individual speaking styles for each character.\n"
            "4. Do not include any introductory or concluding remarks outside the dialogue. The output should start directly with the first speaker's line and end with the last speaker's line."
        )

        return f"{base_system_prompt}\n\n" + self.system_prompt_extra

    @property
    def user_prompt(self) -> str:
        """
        Generates the specific user prompt based on the dataclass attributes.
        This prompt contains the dynamic details for the conversation.
        """
        if self.user_prompt_override:
            return self.user_prompt_override

        character_descriptions = "\n".join(
            f"""- Name: {char.name}\n\t- Role: {char.conversational_role}\n\t- Style: {char.speaking_style}"""
            for char in self.characters
        )

        user_prompt_parts = [
            "Your task is to generate a natural, flowing dialogue based on the following specifications:",
            "",
            f"Overall Conversation Style: {self.overall_conversation_style}",
            "",
            f"Main Topic: {self.main_topic}",
            "",
            f"Characters and Their Defined Roles and Speaking Styles (if supplied):\n{character_descriptions}",
        ]

        if self.scenario:
            user_prompt_parts.append(
                f"\nSpecific Scenario or Context for the Dialogue:\n{self.scenario}"
            )

        user_prompt_parts.append(
            f"\nGenerate a complete dialogue for a conversation approximately {self.dialogue_length}."
        )

        return "\n".join(user_prompt_parts) + f"\n\n{self.user_prompt_extra}"
