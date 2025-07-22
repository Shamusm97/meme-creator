"""Video creation use case with subtitle support using TTS domain models."""

from pathlib import Path
from typing import Optional

from config.domain.models import VideoConfig
from config.infrastructure.json import ConfigurationLoader
from tts.domain.models import AudioScript
from video.domain.models import VideoFile, VideoProject, CharacterScene, VideoClip
from video.infrastructure.moviepy_client import MoviePyVideoClient


class CreateVideoWithSubtitlesUseCase:
    """Creates videos with synchronized subtitles using TTS domain models."""

    def __init__(self):
        pass

    def execute(
        self,
        audio_script: AudioScript,
        video_config: VideoConfig,
        output_path: Path,
        show_progress: bool = True,
    ) -> VideoFile:
        """
        Create a video with subtitles from an audio script.

        Args:
            audio_script: AudioScript containing dialogue and timing information
            video_config: Video configuration including subtitle settings
            output_path: Path where the video should be saved
            show_progress: Whether to display progress during video creation

        Returns:
            VideoFile representing the created video with subtitles
        """
        # Create character scenes from audio script
        character_scenes = []
        current_time = 0.0

        for audio_file in audio_script.audio_files:
            scene = CharacterScene(
                character=audio_file.character,
                audio_file=audio_file,
                start_time=current_time,
                duration=audio_file.duration_seconds or 0.0,
                character_image=audio_file.character.image_path
                if audio_file.character.image_path.exists()
                else None,
            )
            character_scenes.append(scene)
            current_time += audio_file.duration_seconds or 0.0

        # Create video project with subtitle support
        video_project = VideoProject(
            background_clip=VideoClip(path=video_config.background_video),
            character_scenes=character_scenes,
            enable_subtitles=True,  # Enable subtitles for this use case
        )

        # Create MoviePy client and generate video
        from video.application.video_service_factory import VideoServiceFactory

        client = VideoServiceFactory.create_service(video_config)

        return client.create_video_with_subtitles(
            project=video_project,
            audio_script=audio_script,
            output_path=output_path,
            show_progress=show_progress,
        )

    def execute_from_config(
        self,
        audio_script: AudioScript,
        config_path: Path,
        output_filename: Optional[str] = None,
        show_progress: bool = True,
    ) -> VideoFile:
        """
        Create a video with subtitles using configuration file.

        Args:
            audio_script: AudioScript containing dialogue and timing
            config_path: Path to JSON configuration file
            output_filename: Optional custom filename for output video
            show_progress: Whether to display progress during video creation

        Returns:
            VideoFile representing the created video with subtitles
        """
        # Load configuration
        project_config = ConfigurationLoader.load_from_file(config_path)

        if not project_config.video_config:
            raise ValueError(
                "Video configuration is required for subtitle video creation"
            )

        # Set up output paths
        project_dir = project_config.base_output_dir / project_config.project_name
        if output_filename:
            video_output_path = project_dir / "videos" / output_filename
        else:
            video_output_path = (
                project_dir
                / "videos"
                / f"{project_config.project_name}_with_subtitles.mp4"
            )

        return self.execute(
            audio_script=audio_script,
            video_config=project_config.video_config,
            output_path=video_output_path,
            show_progress=show_progress,
        )


def main():
    """Main function demonstrating subtitle video creation."""
    import sys
    from dotenv import load_dotenv
    from tts.application.load_audio_script_use_case import LoadAudioScriptFromDirUseCase

    load_dotenv()

    if len(sys.argv) not in [3, 4]:
        print(
            "Usage: python create_video_with_subtitles_use_case.py <audio_directory> <config_file> [output_filename]"
        )
        print("       output_filename: Optional custom filename for the output video")
        sys.exit(1)

    audio_dir = Path(sys.argv[1])
    config_path = Path(sys.argv[2])
    output_filename = sys.argv[3] if len(sys.argv) > 3 else None

    if not audio_dir.exists():
        print(f"Error: Audio directory not found: {audio_dir}")
        sys.exit(1)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Load audio script
        load_audio_use_case = LoadAudioScriptFromDirUseCase()
        audio_script = load_audio_use_case.execute(audio_dir)

        # Load config to get project info
        project_config = ConfigurationLoader.load_from_file(config_path)

        # Create video with subtitles
        use_case = CreateVideoWithSubtitlesUseCase()
        video_file = use_case.execute_from_config(
            audio_script=audio_script,
            config_path=config_path,
            output_filename=output_filename,
            show_progress=True,
        )

        print(f"Subtitle Video Creation Results for: {project_config.project_name}")
        print("=" * 60)

        print(f"✓ Processed {len(audio_script.audio_files)} audio files")
        print(
            f"✓ Total audio duration: {audio_script.total_duration_seconds:.2f} seconds"
        )

        characters = audio_script.get_characters()
        character_names = [char.name for char in characters]
        print(f"✓ Characters: {', '.join(character_names)}")

        print("\n🔊 Audio Files:")
        for audio_file in audio_script.audio_files:
            print(f"  - {audio_file.character.name}: {audio_file.dialogue[:50]}...")

        print("\n🎬 Video with Subtitles:")
        print(f"  - {video_file.path.name}")
        print(f"  - Size: {video_file.file_size_bytes / 1024 / 1024:.2f} MB")
        if video_file.render_time_seconds:
            print(f"  - Render time: {video_file.render_time_seconds:.2f} seconds")

        print(f"\n📁 Output saved to: {video_file.path}")

    except Exception as e:
        print(f"Error creating video with subtitles: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
