import time
from pathlib import Path

from config.domain.models import MoviePyVideoConfig
from video.domain.models import (
    VideoService,
    VideoProject,
    VideoFile,
    VideoFormat,
    VideoQuality,
)


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
            import moviepy.editor as mp

            self.mp = mp
        except ImportError:
            raise ImportError(
                "moviepy is required for video creation. Install with: pip install moviepy"
            )

    def create_video(self, project: VideoProject, output_path: Path) -> VideoFile:
        """Create a video from a project configuration."""
        start_time = time.time()

        try:
            # Load background video
            background_clip = self.mp.VideoFileClip(str(project.background_clip.path))

            # Create audio clips from character scenes
            audio_clips = []
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

                # Trim to match the audio duration
                final_video = final_video.subclipped(0, total_duration)
            elif total_duration > 0 and total_duration < background_duration:
                # Audio is shorter than background video - trim the video
                final_video = background_clip.subclipped(0, total_duration)
            else:
                # Use background video as-is
                final_video = background_clip

            # Set the audio to the final video
            if final_audio:
                final_video = final_video.with_audio(final_audio)

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the video file
            codec = self._get_codec_for_format(project.output_format)
            fps = self.config.fps

            final_video.write_videofile(
                str(output_path),
                codec=codec,
                fps=fps,
                audio_codec="aac",
                logger=None,
            )

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
            quality=VideoQuality.LOW,  # Use low quality for previews
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
