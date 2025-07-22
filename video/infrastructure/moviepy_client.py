import time
import moviepy
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

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
class MoviePyVideoConfig:
    """Configuration specific to MoviePy video provider"""

    quality: str = field(default="medium")
    fps: int = field(default=30)
    codec: str = field(default="libx264")
    width: Optional[int] = field(default=None)  # Override video width (None = use background video size)
    height: Optional[int] = field(default=None)  # Override video height (None = use background video size)
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


class MoviePyVideoClient(VideoService):
    """MoviePy implementation of VideoService."""

    def __init__(self, config: MoviePyVideoConfig):
        """
        Initialize MoviePy video client.

        Args:
            config: MoviePy configuration
        """
        self.config = config
        # Import moviepy here to avoid import errors if not installed
        try:
            import moviepy as mp

            self.mp = mp
        except ImportError:
            raise ImportError(
                "moviepy is required for video creation. Install with: pip install moviepy"
            )

    def create_video(
        self, project: VideoProject, output_path: Path, show_progress: bool = True
    ) -> VideoFile:
        """Create a video from a project configuration."""
        start_time = time.time()

        try:
            # Load background video
            background_clip = self.mp.VideoFileClip(str(project.background_clip.path))

            # Create audio clips and image overlays from character scenes
            audio_clips = []
            image_clips = []

            for scene in project.character_scenes:
                if scene.audio_file.path.exists():
                    audio_clip = self.mp.AudioFileClip(str(scene.audio_file.path))
                    actual_duration = audio_clip.duration

                    # Use the minimum of actual duration and scene duration to prevent overruns
                    if scene.audio_file.duration_seconds:
                        safe_duration = min(
                            actual_duration, scene.audio_file.duration_seconds
                        )
                    else:
                        safe_duration = actual_duration

                    # Only set duration if it's different from actual duration
                    if safe_duration < actual_duration:
                        audio_clip = audio_clip.with_duration(safe_duration)

                    audio_clip = audio_clip.with_start(scene.start_time)
                    audio_clips.append(audio_clip)

                    # Add character image overlay if available
                    print(
                        f"  Processing scene for {scene.character.name}: image={scene.character_image}"
                    )
                    if scene.character_image and scene.character_image.exists():
                        print(f"  ✓ Loading character image: {scene.character_image}")
                        try:
                            char_image = self.mp.ImageClip(str(scene.character_image))

                            # Set the duration and start time for the image
                            char_image = char_image.with_duration(
                                safe_duration
                            ).with_start(scene.start_time)

                            # Since character images are already full-size with transparent backgrounds
                            # and pre-positioned, just resize to match video dimensions exactly
                            video_width = background_clip.w
                            video_height = background_clip.h
                            char_image = char_image.resized(
                                width=video_width, height=video_height
                            )

                            # Position at (0,0) to overlay the entire video
                            char_image = char_image.with_position((0, 0))

                            image_clips.append(char_image)
                            print(
                                f"  ✓ Added full-size character image clip for {scene.character.name}"
                            )
                        except Exception as e:
                            print(
                                f"  ✗ Error loading character image {scene.character_image}: {e}"
                            )
                            continue
                    else:
                        print(f"  ✗ No character image for {scene.character.name}")

            # Combine audio clips
            final_audio = None
            if audio_clips:
                final_audio = self.mp.CompositeAudioClip(audio_clips)

            # Handle video duration vs audio duration mismatch
            total_duration = project.get_total_duration()
            background_duration = background_clip.duration

            if total_duration > background_duration:
                # Audio is longer than background video - loop the background
                loops_needed = int(total_duration / background_duration) + 1
                looped_clips = [background_clip] * loops_needed
                background_video = self.mp.concatenate_videoclips(looped_clips)

                # Trim to match the audio duration
                background_video = background_video.subclipped(0, total_duration)
            elif total_duration > 0 and total_duration < background_duration:
                # Audio is shorter than background video - trim the video
                background_video = background_clip.subclipped(0, total_duration)
            else:
                # Use background video as-is
                background_video = background_clip

            # Create single composition with all clips at once
            print(
                f"📹 Final composition: {len(image_clips)} character image clips to overlay"
            )
            all_clips = [background_video] + image_clips
            final_video = self.mp.CompositeVideoClip(all_clips)

            # Set the audio to the final video
            if final_audio:
                final_video = final_video.with_audio(final_audio)

            # Apply video size override if specified in config
            if self.config.width or self.config.height:
                target_width = self.config.width or final_video.w
                target_height = self.config.height or final_video.h

                if target_width != final_video.w or target_height != final_video.h:
                    final_video = final_video.resized(
                        width=target_width, height=target_height
                    )

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the video file
            codec = self._get_codec_for_format(project.output_format)
            fps = self.config.fps

            if show_progress:
                print(
                    f"🎬 Rendering video ({int(final_video.w)}x{int(final_video.h)}, {fps}fps)..."
                )

            final_video.write_videofile(
                str(output_path),
                codec=codec,
                fps=fps,
                audio_codec="aac",
                logger="bar" if show_progress else None,
            )

            if show_progress:
                print("✓ Video rendering completed")

            # Clean up resources
            final_video.close()
            background_clip.close()
            for clip in audio_clips:
                clip.close()

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
            background_clip = self.mp.VideoFileClip(str(project.background_clip.path))

            # Create audio clips and image overlays from character scenes
            audio_clips = []
            image_clips = []
            subtitle_clips = []

            for scene in project.character_scenes:
                if scene.audio_file.path.exists():
                    audio_clip = self.mp.AudioFileClip(str(scene.audio_file.path))
                    actual_duration = audio_clip.duration

                    # Use the minimum of actual duration and scene duration to prevent overruns
                    if scene.audio_file.duration_seconds:
                        safe_duration = min(
                            actual_duration, scene.audio_file.duration_seconds
                        )
                    else:
                        safe_duration = actual_duration

                    # Only set duration if it's different from actual duration
                    if safe_duration < actual_duration:
                        audio_clip = audio_clip.with_duration(safe_duration)

                    audio_clip = audio_clip.with_start(scene.start_time)
                    audio_clips.append(audio_clip)

                    # Add character image overlay if available
                    if scene.character_image and scene.character_image.exists():
                        try:
                            char_image = self.mp.ImageClip(str(scene.character_image))
                            char_image = char_image.with_duration(
                                safe_duration
                            ).with_start(scene.start_time)

                            # Resize to match video dimensions
                            video_width = background_clip.w
                            video_height = background_clip.h
                            char_image = char_image.resized(
                                width=video_width, height=video_height
                            )
                            char_image = char_image.with_position((0, 0))

                            image_clips.append(char_image)
                        except Exception as e:
                            print(
                                f"  ✗ Error loading character image {scene.character_image}: {e}"
                            )
                            continue

                    # Create subtitle clip if subtitles are enabled
                    if project.enable_subtitles:
                        subtitle_clip = self._create_subtitle_clip(
                            text=scene.audio_file.dialogue,
                            start_time=scene.start_time,
                            duration=safe_duration,
                            video_size=(background_clip.w, background_clip.h),
                        )
                        subtitle_clips.append(subtitle_clip)

            # Combine audio clips
            final_audio = None
            if audio_clips:
                final_audio = self.mp.CompositeAudioClip(audio_clips)

            # Handle video duration vs audio duration mismatch
            total_duration = project.get_total_duration()
            background_duration = background_clip.duration

            if total_duration > background_duration:
                # Audio is longer than background video - loop the background
                loops_needed = int(total_duration / background_duration) + 1
                looped_clips = [background_clip] * loops_needed
                final_video = self.mp.concatenate_videoclips(looped_clips)
                final_video = final_video.subclipped(0, total_duration)
            elif total_duration > 0 and total_duration < background_duration:
                # Audio is shorter than background video - trim the video
                final_video = background_clip.subclipped(0, total_duration)
            else:
                # Use background video as-is
                final_video = background_clip

            # Composite all clips together
            all_clips = [final_video]
            if image_clips:
                all_clips.extend(image_clips)
            if subtitle_clips:
                all_clips.extend(subtitle_clips)

            if len(all_clips) > 1:
                final_video = self.mp.CompositeVideoClip(all_clips)

            # Set the audio to the final video
            if final_audio:
                final_video = final_video.with_audio(final_audio)

            # Apply video size override if specified in config
            if self.config.width or self.config.height:
                target_width = self.config.width or final_video.w
                target_height = self.config.height or final_video.h

                if target_width != final_video.w or target_height != final_video.h:
                    final_video = final_video.resized(
                        width=target_width, height=target_height
                    )

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the video file
            codec = self._get_codec_for_format(project.output_format)
            fps = self.config.fps

            if show_progress:
                print(
                    f"🎬 Rendering video with subtitles ({int(final_video.w)}x{int(final_video.h)}, {fps}fps)..."
                )

            final_video.write_videofile(
                str(output_path),
                codec=codec,
                fps=fps,
                audio_codec="aac",
                logger="bar" if show_progress else None,
            )

            if show_progress:
                print("✓ Video rendering completed")

            # Clean up resources
            final_video.close()
            background_clip.close()
            for clip in audio_clips:
                clip.close()

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

    def _create_subtitle_clip(
        self, text: str, start_time: float, duration: float, video_size: tuple
    ):
        """Create a subtitle clip with the configured styling."""
        subtitle_config = self.config.subtitles

        if not subtitle_config.enabled:
            return None

        # Create text clip
        txt_clip = self.mp.TextClip(
            subtitle_config.font_name,
            text=text,
            font_size=subtitle_config.font_size,
            color=subtitle_config.font_color,
            stroke_color=subtitle_config.stroke_color,
            stroke_width=subtitle_config.stroke_width,
        )

        # Position subtitle based on configuration
        video_width, video_height = video_size
        margin = subtitle_config.margin

        if subtitle_config.position == "bottom":
            position = ("center", video_height - txt_clip.h - margin)
        elif subtitle_config.position == "top":
            position = ("center", margin)
        elif subtitle_config.position == "center":
            position = ("center", "center")
        else:
            position = (
                "center",
                video_height - txt_clip.h - margin,
            )  # Default to bottom

        txt_clip = (
            txt_clip.with_position(position)
            .with_start(start_time)
            .with_duration(duration)
        )

        return txt_clip

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
