"""Use case for creating videos from speech scripts."""

from pathlib import Path

from config.domain.models import VideoConfig
from tts.domain.models import AudioScript
from video.domain.models import (
    VideoProject,
    VideoClip,
    CharacterScene,
    VideoFormat,
    VideoQuality,
    VideoFile,
)
from video.application.video_service_factory import VideoServiceFactory


class CreateVideoUseCase:
    """Use case for creating videos from speech scripts."""

    def execute(
        self, audio_script: AudioScript, video_config: VideoConfig, output_path: Path
    ) -> VideoFile:
        """
        Create a video from an audio script.

        Args:
            audio_script: Audio script with audio files
            video_config: Video configuration
            output_path: Where to save the final video

        Returns:
            VideoFile representing the created video
        """
        # Create video service
        video_service = VideoServiceFactory.create_service(video_config)

        # Create video project from audio script
        project = self._create_video_project(audio_script, video_config)

        # Create the video
        return video_service.create_video(project, output_path)

    def _create_video_project(
        self, audio_script: AudioScript, video_config: VideoConfig
    ) -> VideoProject:
        """Convert audio script to video project."""

        # Create background video clip
        background_clip = VideoClip(
            path=video_config.background_video,
            start_time=0.0,
            duration=audio_script.total_duration_seconds,
        )

        # Create character scenes from audio files
        character_scenes = []
        current_time = 0.0

        for audio_file in audio_script.audio_files:
            # Get character image path if available
            character_image = None
            if (
                audio_file.character.image_path
                and audio_file.character.image_path.exists()
            ):
                character_image = audio_file.character.image_path

            # Create character scene
            scene = CharacterScene(
                character=audio_file.character,
                audio_file=audio_file,
                start_time=current_time,
                duration=audio_file.duration_seconds
                or 3.0,  # Default 3 seconds if duration unknown
                character_image=character_image,
            )

            character_scenes.append(scene)
            current_time += scene.duration

        # Create video project
        return VideoProject(
            background_clip=background_clip,
            character_scenes=character_scenes,
            output_format=VideoFormat.MP4,  # Default to MP4
            quality=VideoQuality.MEDIUM,  # Default to medium quality
        )

