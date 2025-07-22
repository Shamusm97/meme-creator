"""Meme creation use case that starts from existing audio files."""

from pathlib import Path
from typing import Optional

from config.domain.models import VideoConfig
from config.infrastructure.json import ConfigurationLoader
from tts.application.load_audio_script_from_dir_use_case import (
    LoadAudioScriptFromDirUseCase,
)
from tts.application.merge_audio_script_use_case import MergeAudioScriptUseCase
from video.application.create_video_use_case import CreateVideoUseCase
from tts.domain.models import AudioScript, AudioFile
from video.domain.models import VideoFile


class MemeFromAudioUseCase:
    """Creates memes from existing audio files, skipping script generation and TTS."""

    def __init__(self):
        self.load_audio_use_case = LoadAudioScriptFromDirUseCase()
        self.merge_use_case = MergeAudioScriptUseCase()
        self.video_use_case = CreateVideoUseCase()

    def execute(
        self,
        audio_dir: Path,
        video_config: VideoConfig,
        output_video_path: Path,
        merge_audio: bool = True,
        delay_between_files: float = 0.0,
    ) -> tuple[AudioScript, Optional[AudioFile], VideoFile]:
        """
        Create a meme video from existing audio files.

        Args:
            audio_dir: Directory containing audio files
            video_config: Video configuration for meme creation
            output_video_path: Where to save the final video
            merge_audio: Whether to merge individual audio files into one file
            delay_between_files: Seconds of silence between merged audio files

        Returns:
            Tuple of (audio_script, merged_audio_file, video_file)
        """
        # Step 1: Load existing audio files
        audio_script = self.load_audio_use_case.execute(audio_dir)

        # Step 2: Optionally merge audio files
        merged_audio_file = None
        if merge_audio and audio_script.audio_files:
            merged_output_path = (
                output_video_path.parent / f"{output_video_path.stem}_merged.wav"
            )
            merged_audio_file = self.merge_use_case.execute(
                audio_script=audio_script,
                output_path=merged_output_path,
                delay_between_files=delay_between_files,
                show_progress=True,
            )

        # Step 3: Create video
        video_file = self.video_use_case.execute(
            audio_script=audio_script,
            video_config=video_config,
            output_path=output_video_path,
            show_progress=True,
        )

        return audio_script, merged_audio_file, video_file

    def execute_from_config(
        self,
        audio_dir: Path,
        config_path: Path,
        merge_audio: bool = True,
        delay_between_files: float = 0.0,
    ) -> tuple[AudioScript, Optional[AudioFile], VideoFile]:
        """
        Create a meme video using configuration file for video settings.

        Args:
            audio_dir: Directory containing audio files
            config_path: Path to JSON configuration file (for video config)
            merge_audio: Whether to merge individual audio files into one file
            delay_between_files: Seconds of silence between merged audio files

        Returns:
            Tuple of (audio_script, merged_audio_file, video_file)
        """
        # Load configuration
        project_config = ConfigurationLoader.load_from_file(config_path)

        if not project_config.video_config:
            raise ValueError("Video configuration is required")

        # Set up output paths
        project_dir = project_config.base_output_dir / project_config.project_name
        video_output_path = (
            project_dir / "videos" / f"{project_config.project_name}_from_audio.mp4"
        )

        return self.execute(
            audio_dir=audio_dir,
            video_config=project_config.video_config,
            output_video_path=video_output_path,
            merge_audio=merge_audio,
            delay_between_files=delay_between_files,
        )


def main():
    """Main function demonstrating meme creation from audio files."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) not in [3, 4]:
        print(
            "Usage: python meme_from_audio_use_case.py <audio_directory> <config_file> [merge_audio]"
        )
        print("       merge_audio: true/false (default: true)")
        sys.exit(1)

    audio_dir = Path(sys.argv[1])
    config_path = Path(sys.argv[2])
    merge_audio = sys.argv[3].lower() != "false" if len(sys.argv) > 3 else True

    if not audio_dir.exists():
        print(f"Error: Audio directory not found: {audio_dir}")
        sys.exit(1)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Load config to get project info
        project_config = ConfigurationLoader.load_from_file(config_path)

        use_case = MemeFromAudioUseCase()
        audio_script, merged_audio, video_file = use_case.execute_from_config(
            audio_dir=audio_dir,
            config_path=config_path,
            merge_audio=merge_audio,
        )

        print(f"Meme Creation from Audio Results for: {project_config.project_name}")
        print("=" * 60)

        print(f"✓ Loaded {len(audio_script.audio_files)} audio files")
        print(f"✓ Total duration: {audio_script.total_duration_seconds:.2f} seconds")

        characters = audio_script.get_characters()
        character_names = [char.name for char in characters]
        print(f"✓ Characters: {', '.join(character_names)}")

        print("\n🔊 Audio Files:")
        for audio_file in audio_script.audio_files:
            print(f"  - {audio_file.path.name} ({audio_file.duration_seconds:.1f}s)")

        if merged_audio:
            print("\n🎵 Merged Audio:")
            print(f"  - {merged_audio.path.name}")
            print(f"  - Duration: {merged_audio.duration_seconds:.2f} seconds")
            print(f"  - Size: {merged_audio.file_size_bytes / 1024 / 1024:.2f} MB")

        print("\n🎬 Video:")
        print(f"  - {video_file.path.name}")
        print(f"  - Size: {video_file.file_size_bytes / 1024 / 1024:.2f} MB")
        if video_file.render_time_seconds:
            print(f"  - Render time: {video_file.render_time_seconds:.2f} seconds")

        print(f"\n📁 Output saved to: {video_file.path}")

    except Exception as e:
        print(f"Error creating meme from audio: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
