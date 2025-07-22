import time
import movis as mv
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np

from video.domain.models import (
    VideoService,
    VideoProject,
    VideoFile,
    VideoFormat,
    VideoQuality,
)
from tts.domain.models import AudioScript


@dataclass
class SubtitleConfig:
    """Configuration for subtitle display"""

    enabled: bool = field(default=True)
    font_name: str = field(default="Arial")
    font_size: int = field(default=48)
    font_color: str = field(default="white")
    stroke_color: str = field(default="black")
    stroke_width: int = field(default=2)
    position: str = field(default="bottom")  # "top", "center", "bottom"
    margin: int = field(default=50)  # Distance from edge in pixels

    def __post_init__(self):
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if not self.font_name.strip():
            raise ValueError("font_name cannot be empty")
        if self.font_size <= 0:
            raise ValueError("font_size must be positive")
        if not self.font_color.strip():
            raise ValueError("font_color cannot be empty")
        if not self.stroke_color.strip():
            raise ValueError("stroke_color cannot be empty")
        if self.stroke_width < 0:
            raise ValueError("stroke_width must be non-negative")
        valid_positions = ["top", "center", "bottom"]
        if self.position not in valid_positions:
            raise ValueError(f"position must be one of: {valid_positions}")
        if self.margin < 0:
            raise ValueError("margin must be non-negative")


@dataclass
class MovisVideoConfig:
    """Configuration specific to Movis video provider"""

    quality: str = field(default="medium")
    fps: int = field(default=30)
    codec: str = field(default="libx264")
    width: Optional[int] = field(default=None)  # Override video width
    height: Optional[int] = field(default=None)  # Override video height
    subtitles: SubtitleConfig = field(default_factory=SubtitleConfig)

    def __post_init__(self):
        valid_qualities = ["low", "medium", "high", "ultra"]
        if self.quality not in valid_qualities:
            raise ValueError(f"Quality must be one of: {valid_qualities}")
        if self.fps <= 0:
            raise ValueError("FPS must be positive")
        if not self.codec.strip():
            raise ValueError("Codec cannot be empty")
        if self.width is not None and self.width <= 0:
            raise ValueError("Width must be positive")
        if self.height is not None and self.height <= 0:
            raise ValueError("Height must be positive")
        if not isinstance(self.subtitles, SubtitleConfig):
            raise ValueError("subtitles must be a SubtitleConfig instance")


class MovisVideoClient(VideoService):
    """Movis implementation of VideoService."""

    def __init__(self, config: MovisVideoConfig):
        """
        Initialize Movis video client.

        Args:
            config: Movis configuration
        """
        self.config = config

    def create_video(
        self, project: VideoProject, output_path: Path, show_progress: bool = True
    ) -> VideoFile:
        """Create a video from a project configuration."""
        start_time = time.time()

        try:
            # Load background video
            background_video = mv.VideoFileClip(str(project.background_clip.path))
            background_duration = background_video.duration

            # Calculate total duration based on scenes
            total_duration = project.get_total_duration()

            # Determine final video dimensions
            if self.config.width and self.config.height:
                video_width = self.config.width
                video_height = self.config.height
            else:
                video_width = background_video.size[0]
                video_height = background_video.size[1]

            # Create composition with determined duration
            scene_duration = (
                max(total_duration, background_duration)
                if total_duration > 0
                else background_duration
            )
            scene = mv.Scene(
                size=(video_width, video_height),
                duration=scene_duration,
                fps=self.config.fps,
            )

            # Handle background video duration
            if total_duration > background_duration and total_duration > 0:
                # Loop background video if audio is longer
                loops_needed = int(total_duration / background_duration) + 1
                for i in range(loops_needed):
                    loop_start = i * background_duration
                    if loop_start < total_duration:
                        # Create a layer for this loop iteration
                        bg_layer = scene.add_layer(
                            background_video,
                            name=f"background_{i}",
                            offset=loop_start,
                            duration=min(
                                background_duration, total_duration - loop_start
                            ),
                        )
                        if (
                            video_width != background_video.size[0]
                            or video_height != background_video.size[1]
                        ):
                            bg_layer.scale(video_width / background_video.size[0])
            else:
                # Use background video as-is or trim if needed
                duration_to_use = (
                    min(background_duration, total_duration)
                    if total_duration > 0
                    else background_duration
                )
                bg_layer = scene.add_layer(
                    background_video,
                    name="background",
                    offset=0,
                    duration=duration_to_use,
                )
                if (
                    video_width != background_video.size[0]
                    or video_height != background_video.size[1]
                ):
                    bg_layer.scale(video_width / background_video.size[0])

            # Process character scenes
            audio_layers = []

            for idx, char_scene in enumerate(project.character_scenes):
                if char_scene.audio_file.path.exists():
                    # Add audio
                    audio_clip = mv.AudioFileClip(str(char_scene.audio_file.path))
                    actual_duration = audio_clip.duration

                    # Use safe duration
                    if char_scene.audio_file.duration_seconds:
                        safe_duration = min(
                            actual_duration, char_scene.audio_file.duration_seconds
                        )
                    else:
                        safe_duration = actual_duration

                    audio_layer = scene.add_layer(
                        audio_clip,
                        name=f"audio_{idx}",
                        offset=char_scene.start_time,
                        duration=safe_duration,
                    )
                    audio_layers.append(audio_layer)

                    # Add character image if available
                    if show_progress:
                        print(
                            f"  Processing scene for {char_scene.character.name}: image={char_scene.character_image}"
                        )

                    if (
                        char_scene.character_image
                        and char_scene.character_image.exists()
                    ):
                        if show_progress:
                            print(
                                f"  ✓ Loading character image: {char_scene.character_image}"
                            )
                        try:
                            # Load image as ImageClip
                            char_image = mv.ImageClip(str(char_scene.character_image))

                            # Add as layer with proper timing
                            img_layer = scene.add_layer(
                                char_image,
                                name=f"character_{idx}",
                                offset=char_scene.start_time,
                                duration=safe_duration,
                            )

                            # Scale to match video dimensions (images are full-size with transparency)
                            img_layer.scale(video_width / char_image.size[0])

                            # Position at center (0, 0) since images are pre-positioned
                            img_layer.position.value = (0, 0)

                            if show_progress:
                                print(
                                    f"  ✓ Added full-size character image clip for {char_scene.character.name}"
                                )
                        except Exception as e:
                            if show_progress:
                                print(
                                    f"  ✗ Error loading character image {char_scene.character_image}: {e}"
                                )
                            continue
                    else:
                        if show_progress:
                            print(
                                f"  ✗ No character image for {char_scene.character.name}"
                            )

            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Render the video
            if show_progress:
                print(
                    f"🎬 Rendering video ({video_width}x{video_height}, {self.config.fps}fps)..."
                )

            # Configure export settings based on format
            codec = self._get_codec_for_format(project.output_format)

            # Export with progress callback if requested
            if show_progress:
                scene.export(
                    str(output_path),
                    codec=codec,
                    audio_codec="aac",
                    progress_callback=lambda p: print(
                        f"\rProgress: {p * 100:.1f}%", end="", flush=True
                    ),
                )
                print("\n✓ Video rendering completed")
            else:
                scene.export(str(output_path), codec=codec, audio_codec="aac")

            render_time = time.time() - start_time
            file_size = output_path.stat().st_size if output_path.exists() else 0

            return VideoFile(
                path=output_path,
                project=project,
                file_size_bytes=file_size,
                render_time_seconds=render_time,
            )

        except Exception as e:
            render_time = time.time() - start_time
            raise Exception(f"Video creation failed after {render_time:.2f}s: {str(e)}")

    def create_video_with_subtitles(
        self,
        project: VideoProject,
        audio_script: AudioScript,
        output_path: Path,
        show_progress: bool = True,
    ) -> VideoFile:
        """Create a video with subtitles from a project configuration and audio script."""
        start_time = time.time()

        try:
            # Load background video
            background_video = mv.VideoFileClip(str(project.background_clip.path))
            background_duration = background_video.duration

            # Calculate total duration
            total_duration = project.get_total_duration()

            # Determine final video dimensions
            if self.config.width and self.config.height:
                video_width = self.config.width
                video_height = self.config.height
            else:
                video_width = background_video.size[0]
                video_height = background_video.size[1]

            # Create composition
            scene_duration = (
                max(total_duration, background_duration)
                if total_duration > 0
                else background_duration
            )
            scene = mv.Scene(
                size=(video_width, video_height),
                duration=scene_duration,
                fps=self.config.fps,
            )

            # Add background video (with looping if needed)
            if total_duration > background_duration and total_duration > 0:
                loops_needed = int(total_duration / background_duration) + 1
                for i in range(loops_needed):
                    loop_start = i * background_duration
                    if loop_start < total_duration:
                        bg_layer = scene.add_layer(
                            background_video,
                            name=f"background_{i}",
                            offset=loop_start,
                            duration=min(
                                background_duration, total_duration - loop_start
                            ),
                        )
                        if (
                            video_width != background_video.size[0]
                            or video_height != background_video.size[1]
                        ):
                            bg_layer.scale(video_width / background_video.size[0])
            else:
                duration_to_use = (
                    min(background_duration, total_duration)
                    if total_duration > 0
                    else background_duration
                )
                bg_layer = scene.add_layer(
                    background_video,
                    name="background",
                    offset=0,
                    duration=duration_to_use,
                )
                if (
                    video_width != background_video.size[0]
                    or video_height != background_video.size[1]
                ):
                    bg_layer.scale(video_width / background_video.size[0])

            # Process character scenes
            for idx, char_scene in enumerate(project.character_scenes):
                if char_scene.audio_file.path.exists():
                    # Add audio
                    audio_clip = mv.AudioFileClip(str(char_scene.audio_file.path))
                    actual_duration = audio_clip.duration

                    if char_scene.audio_file.duration_seconds:
                        safe_duration = min(
                            actual_duration, char_scene.audio_file.duration_seconds
                        )
                    else:
                        safe_duration = actual_duration

                    scene.add_layer(
                        audio_clip,
                        name=f"audio_{idx}",
                        offset=char_scene.start_time,
                        duration=safe_duration,
                    )

                    # Add character image if available
                    if (
                        char_scene.character_image
                        and char_scene.character_image.exists()
                    ):
                        try:
                            char_image = mv.ImageClip(str(char_scene.character_image))
                            img_layer = scene.add_layer(
                                char_image,
                                name=f"character_{idx}",
                                offset=char_scene.start_time,
                                duration=safe_duration,
                            )
                            img_layer.scale(video_width / char_image.size[0])
                            img_layer.position.value = (0, 0)
                        except Exception as e:
                            if show_progress:
                                print(f"Error loading character image: {e}")
                            continue

                    # Add subtitle if enabled
                    if project.enable_subtitles and self.config.subtitles.enabled:
                        subtitle_layer = self._create_subtitle_layer(
                            scene=scene,
                            text=char_scene.audio_file.dialogue,
                            start_time=char_scene.start_time,
                            duration=safe_duration,
                            video_size=(video_width, video_height),
                            layer_name=f"subtitle_{idx}",
                        )

            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Render the video
            if show_progress:
                print(
                    f"🎬 Rendering video with subtitles ({video_width}x{video_height}, {self.config.fps}fps)..."
                )

            codec = self._get_codec_for_format(project.output_format)

            if show_progress:
                scene.export(
                    str(output_path),
                    codec=codec,
                    audio_codec="aac",
                    progress_callback=lambda p: print(
                        f"\rProgress: {p * 100:.1f}%", end="", flush=True
                    ),
                )
                print("\n✓ Video rendering completed")
            else:
                scene.export(str(output_path), codec=codec, audio_codec="aac")

            render_time = time.time() - start_time
            file_size = output_path.stat().st_size if output_path.exists() else 0

            return VideoFile(
                path=output_path,
                project=project,
                file_size_bytes=file_size,
                render_time_seconds=render_time,
            )

        except Exception as e:
            render_time = time.time() - start_time
            raise Exception(
                f"Video creation with subtitles failed after {render_time:.2f}s: {str(e)}"
            )

    def _create_subtitle_layer(
        self,
        scene: mv.Scene,
        text: str,
        start_time: float,
        duration: float,
        video_size: tuple,
        layer_name: str,
    ):
        """Create a subtitle layer with the configured styling."""
        subtitle_config = self.config.subtitles

        if not subtitle_config.enabled:
            return None

        video_width, video_height = video_size

        # Create text clip
        text_clip = mv.Text(
            text=text,
            font_family=subtitle_config.font_name,
            font_size=subtitle_config.font_size,
            color=subtitle_config.font_color,
            stroke_color=subtitle_config.stroke_color,
            stroke_width=subtitle_config.stroke_width,
            duration=duration,
        )

        # Add text layer to scene
        text_layer = scene.add_layer(
            text_clip, name=layer_name, offset=start_time, duration=duration
        )

        # Position subtitle based on configuration
        margin = subtitle_config.margin

        if subtitle_config.position == "bottom":
            # Position at bottom center
            text_layer.position.value = (
                0,
                video_height / 2 - margin - subtitle_config.font_size,
            )
        elif subtitle_config.position == "top":
            # Position at top center
            text_layer.position.value = (
                0,
                -video_height / 2 + margin + subtitle_config.font_size,
            )
        elif subtitle_config.position == "center":
            # Position at center
            text_layer.position.value = (0, 0)
        else:
            # Default to bottom
            text_layer.position.value = (
                0,
                video_height / 2 - margin - subtitle_config.font_size,
            )

        return text_layer

    def preview_video(
        self, project: VideoProject, output_path: Path, duration_seconds: float = 10.0
    ) -> VideoFile:
        """Create a preview of the video project."""
        # Create a temporary project with limited duration
        preview_project = VideoProject(
            background_clip=project.background_clip,
            character_scenes=[
                scene
                for scene in project.character_scenes
                if scene.start_time < duration_seconds
            ],
            output_format=project.output_format,
            quality=VideoQuality.LOW,
        )

        # Limit scene durations to fit within preview
        for scene in preview_project.character_scenes:
            if scene.start_time + scene.duration > duration_seconds:
                scene.duration = duration_seconds - scene.start_time

        # Generate preview using the provided output path
        return self.create_video(preview_project, output_path)

    def _get_codec_for_format(self, format: VideoFormat) -> str:
        """Get appropriate codec for video format."""
        codec_map = {
            VideoFormat.MP4: "libx264",
            VideoFormat.AVI: "libxvid",
            VideoFormat.MOV: "libx264",
        }
        return codec_map.get(format, self.config.codec)

    def _get_quality_settings(self) -> dict:
        """Get encoding quality settings based on config."""
        quality_presets = {
            "low": {"crf": 28, "preset": "faster"},
            "medium": {"crf": 23, "preset": "medium"},
            "high": {"crf": 18, "preset": "slow"},
            "ultra": {"crf": 15, "preset": "slower"},
        }
        return quality_presets.get(self.config.quality, quality_presets["medium"])
