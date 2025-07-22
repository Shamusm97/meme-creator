from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from enum import Enum

from config.domain.models import Character
from script.domain.models import Script, ScriptEntry


@dataclass
class VoiceProfile:
    """Represents a voice profile configuration."""

    temperature: float = field(default=0.8)
    exaggeration: float = field(default=0.5)
    cfg_weight: float = field(default=0.5)
    seed: int = field(default=0)
    speed_factor: float = field(default=1.0)
    language: str = field(default="en")

    def __post_init__(self):
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if not 0 <= self.exaggeration <= 2:
            raise ValueError("Exaggeration must be between 0 and 2")
        if not 0 <= self.cfg_weight <= 1:
            raise ValueError("CFG weight must be between 0 and 1")
        if self.seed < 0:
            raise ValueError("Seed must be non-negative")
        if self.speed_factor <= 0:
            raise ValueError("Speed factor must be positive")


class VoiceMode(Enum):
    """Voice synthesis modes."""

    PREDEFINED = "predefined"
    CLONE = "clone"


class OutputFormat(Enum):
    """Audio output formats."""

    WAV = "wav"
    OPUS = "opus"


@dataclass
class TTSRequest:
    """Domain model for text-to-speech requests."""

    script_entry: ScriptEntry
    voice_mode: VoiceMode = field(default=VoiceMode.PREDEFINED)
    predefined_voice_id: Optional[str] = field(default=None)
    reference_audio_filename: Optional[str] = field(default=None)
    output_format: OutputFormat = field(default=OutputFormat.WAV)
    split_text: bool = field(default=True)
    chunk_size: int = field(default=120)
    voice_profile: Optional[VoiceProfile] = field(default=None)

    def __post_init__(self):
        if not self.script_entry.content.strip():
            raise ValueError("Script entry content cannot be empty")

        if self.voice_mode == VoiceMode.PREDEFINED and not self.predefined_voice_id:
            raise ValueError(
                "predefined_voice_id is required when voice_mode is 'predefined'"
            )

        if self.voice_mode == VoiceMode.CLONE and not self.reference_audio_filename:
            raise ValueError(
                "reference_audio_filename is required when voice_mode is 'clone'"
            )

        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be positive")


@dataclass
class AudioFile:
    """Domain model representing an audio file."""

    path: Path
    script_entry: Optional[ScriptEntry] = field(default=None)
    duration_seconds: Optional[float] = field(default=None)
    file_size_bytes: Optional[int] = field(default=None)

    def __post_init__(self):
        if not self.path.exists():
            raise ValueError(f"Audio file does not exist: {self.path}")
        if self.script_entry and not self.script_entry.content.strip():
            raise ValueError("Script entry content cannot be empty")


@dataclass
class AudioScript:
    """Domain model for a complete speech script with timing."""

    audio_files: List[AudioFile] = field(default_factory=list)
    source_script: Optional[Script] = field(default=None)

    def add_audio_file(self, audio_file: AudioFile) -> None:
        """Add an audio file to the script."""
        self.audio_files.append(audio_file)

    def get_characters(self) -> List[Character]:
        """Get unique characters in the script."""
        seen_names = set()
        unique_characters = []
        for af in self.audio_files:
            if af.script_entry and af.script_entry.character.name not in seen_names:
                seen_names.add(af.script_entry.character.name)
                unique_characters.append(af.script_entry.character)
        return unique_characters

    def get_files_by_character(self, character: Character) -> List[AudioFile]:
        """Get all audio files for a specific character."""
        return [
            af
            for af in self.audio_files
            if af.script_entry and af.script_entry.character == character
        ]

    @property
    def total_duration_seconds(self) -> float:
        """Calculate total duration of all audio files."""
        return sum(af.duration_seconds or 0 for af in self.audio_files)


class TTSService(ABC):
    """Abstract domain service for text-to-speech operations."""

    @abstractmethod
    def synthesize(self, request: TTSRequest, output_dir: Path) -> AudioFile:
        """
        Synthesize speech for a single request.

        Args:
            request: TTS request with text and configuration
            output_dir: Where to save the audio file

        Returns:
            Result of the synthesis operation
        """
        pass

    @abstractmethod
    def synthesize_script(
        self, requests: List[TTSRequest], output_dir: Path
    ) -> AudioScript:
        """
        Synthesize speech for multiple requests (complete script).

        Args:
            requests: List of TTS requests
            output_dir: Directory to save audio files

        Returns:
            Complete speech script with audio files
        """
        pass
