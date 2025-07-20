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
        # Validate project name by checking if it is a non-empty string and
        # replacing spaces with underscores
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
class ChatterboxTTSConfig:
    """Configuration specific to Chatterbox TTS provider"""

    base_url: str
    endpoint: str = field(default="/tts")
    timeout: int = field(default=120)

    def __post_init__(self):
        if not self.base_url.strip():
            raise ValueError("Base URL cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class TTSConfig:
    """Configuration for text-to-speech settings"""

    provider: str
    chatterbox: Optional[ChatterboxTTSConfig] = field(default=None)

    def __post_init__(self):
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("Provider must be a non-empty string")

        provider_lower = self.provider.lower()
        if provider_lower == "chatterbox":
            if self.chatterbox is None:
                raise ValueError(
                    "Chatterbox configuration is required when provider is 'chatterbox'"
                )
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

    def get_provider_config(self) -> ChatterboxTTSConfig:
        """Get the provider-specific configuration"""
        if self.provider.lower() == "chatterbox":
            assert self.chatterbox is not None, (
                "Chatterbox config should not be None here"
            )
            return self.chatterbox
        raise ValueError(f"No configuration available for provider: {self.provider}")


@dataclass
class MoviePyVideoConfig:
    """Configuration specific to MoviePy video provider"""

    quality: str = field(default="medium")
    fps: int = field(default=30)
    codec: str = field(default="libx264")

    def __post_init__(self):
        valid_qualities = ["low", "medium", "high", "ultra"]
        if self.quality not in valid_qualities:
            raise ValueError(f"Quality must be one of: {valid_qualities}")
        if self.fps <= 0:
            raise ValueError("FPS must be positive")
        if not self.codec.strip():
            raise ValueError("Codec cannot be empty")


@dataclass
class VideoConfig:
    """Configuration for the video generation process"""

    provider: str
    background_video: Path
    moviepy: Optional[MoviePyVideoConfig] = field(default=None)

    def __post_init__(self):
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("Provider must be a non-empty string")
        if not self.background_video or not Path(self.background_video).exists():
            raise ValueError(
                f"Background video file does not exist: {self.background_video}"
            )

        provider_lower = self.provider.lower()
        if provider_lower == "moviepy":
            if self.moviepy is None:
                self.moviepy = MoviePyVideoConfig()
        else:
            raise ValueError(f"Unsupported video provider: {self.provider}")

    def get_provider_config(self) -> MoviePyVideoConfig:
        """Get the provider-specific configuration"""
        if self.provider.lower() == "moviepy":
            assert self.moviepy is not None, "MoviePy config should not be None here"
            return self.moviepy
        raise ValueError(f"No configuration available for provider: {self.provider}")


@dataclass
class ThinkingConfig:
    """Configuration for LLM thinking mode"""

    include_thoughts: bool = field(default=False)
    thinking_budget: int = field(default=0)

    def __post_init__(self):
        if not isinstance(self.include_thoughts, bool):
            raise ValueError("include_thoughts must be a boolean")
        if (
            not isinstance(self.thinking_budget, (int, float))
            or self.thinking_budget < 0
        ):
            raise ValueError("thinking_budget must be a non-negative number")
        self.thinking_budget = int(self.thinking_budget)


@dataclass
class GeminiLLMConfig:
    """Configuration specific to Gemini LLM provider"""

    temperature: float = field(default=0.7)
    max_output_tokens: int = field(default=1024)
    model: str = field(default="gemini-2.5-flash")
    direct_output: bool = field(default=False)
    thinking_config: ThinkingConfig = field(default_factory=ThinkingConfig)

    def __post_init__(self):
        if (
            not isinstance(self.temperature, (int, float))
            or not 0 <= self.temperature <= 2
        ):
            raise ValueError("Temperature must be a number between 0 and 2")
        if not isinstance(self.max_output_tokens, int) or self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Model must be a non-empty string")
        if not isinstance(self.direct_output, bool):
            raise ValueError("direct_output must be a boolean")
        if not isinstance(self.thinking_config, ThinkingConfig):
            raise ValueError("thinking_config must be a ThinkingConfig instance")


@dataclass
class LLMConfig:
    """Configuration for the LLM client"""

    provider: str
    gemini: Optional[GeminiLLMConfig] = field(default=None)
    api_key: str = field(default="")

    def __post_init__(self):
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("Provider must be a non-empty string")

        provider_lower = self.provider.lower()
        if provider_lower == "gemini":
            if self.gemini is None:
                self.gemini = GeminiLLMConfig()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def get_provider_config(self) -> GeminiLLMConfig:
        """Get the provider-specific configuration"""
        if self.provider.lower() == "gemini":
            assert self.gemini is not None, "Gemini config should not be None here"
            return self.gemini
        raise ValueError(f"No configuration available for provider: {self.provider}")


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
