"""Domain models for video creation and editing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from enum import Enum

from config.domain.models import Character
from tts.domain.models import AudioFile


class VideoFormat(Enum):
    """Video output formats."""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"


class VideoQuality(Enum):
    """Video quality presets."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class VideoClip:
    """Domain model representing a video clip."""
    
    path: Path
    start_time: float = field(default=0.0)
    duration: Optional[float] = field(default=None)
    
    def __post_init__(self):
        if not self.path.exists():
            raise ValueError(f"Video file does not exist: {self.path}")
        if self.start_time < 0:
            raise ValueError("Start time cannot be negative")
        if self.duration is not None and self.duration <= 0:
            raise ValueError("Duration must be positive")


@dataclass
class CharacterScene:
    """Domain model representing a character's scene in the video."""
    
    character: Character
    audio_file: AudioFile
    start_time: float
    duration: float
    character_image: Optional[Path] = field(default=None)
    
    def __post_init__(self):
        if self.start_time < 0:
            raise ValueError("Start time cannot be negative")
        if self.duration <= 0:
            raise ValueError("Duration must be positive")
        if self.character_image and not self.character_image.exists():
            raise ValueError(f"Character image does not exist: {self.character_image}")


@dataclass
class VideoProject:
    """Domain model representing a complete video project."""
    
    background_clip: VideoClip
    character_scenes: List[CharacterScene] = field(default_factory=list)
    output_format: VideoFormat = field(default=VideoFormat.MP4)
    quality: VideoQuality = field(default=VideoQuality.MEDIUM)
    
    def add_character_scene(self, scene: CharacterScene) -> None:
        """Add a character scene to the project."""
        self.character_scenes.append(scene)
    
    def get_total_duration(self) -> float:
        """Calculate total video duration."""
        if not self.character_scenes:
            return 0.0
        return max(scene.start_time + scene.duration for scene in self.character_scenes)
    
    def get_characters(self) -> List[Character]:
        """Get unique characters in the project."""
        return list(set(scene.character for scene in self.character_scenes))
    
    def get_scenes_by_character(self, character: Character) -> List[CharacterScene]:
        """Get all scenes for a specific character."""
        return [scene for scene in self.character_scenes if scene.character == character]


@dataclass
class VideoFile:
    """Domain model representing a created video file."""
    
    path: Path
    project: VideoProject
    file_size_bytes: Optional[int] = field(default=None)
    render_time_seconds: Optional[float] = field(default=None)
    
    def __post_init__(self):
        if not self.path.exists():
            raise ValueError(f"Video file does not exist: {self.path}")
        if self.file_size_bytes is not None and self.file_size_bytes < 0:
            raise ValueError("File size cannot be negative")
        if self.render_time_seconds is not None and self.render_time_seconds < 0:
            raise ValueError("Render time cannot be negative")


class VideoService(ABC):
    """Abstract domain service for video creation and editing."""

    @abstractmethod
    def create_video(self, project: VideoProject, output_path: Path) -> VideoFile:
        """
        Create a video from a project configuration.
        
        Args:
            project: Video project with all scenes and configuration
            output_path: Where to save the final video
            
        Returns:
            VideoFile representing the created video
        """
        pass

    @abstractmethod
    def preview_video(self, project: VideoProject, output_path: Path, duration_seconds: float = 10.0) -> VideoFile:
        """
        Create a preview of the video project.
        
        Args:
            project: Video project to preview
            output_path: Where to save the preview video
            duration_seconds: Length of preview in seconds
            
        Returns:
            VideoFile representing the preview video
        """
        pass