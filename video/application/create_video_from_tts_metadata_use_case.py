"""Video creation use case using TTS metadata JSON for subtitles."""

from pathlib import Path
from typing import Optional

from config.domain.models import VideoConfig, Character
from config.infrastructure.json import ConfigurationLoader
from tts.domain.models import AudioFile, AudioScript
from tts.infrastructure.audio_script_metadata_writer import AudioScriptMetadataWriter
from video.domain.models import VideoFile, VideoProject, CharacterScene, VideoClip
from video.infrastructure.moviepy_client import MoviePyVideoClient


class CreateVideoFromTTSMetadataUseCase:
    """Creates videos with subtitles using TTS metadata JSON as source."""

    def __init__(self):
        self.metadata_writer = AudioScriptMetadataWriter()

    def execute(
        self,
        tts_metadata_json: Path,
        video_config: VideoConfig,
        output_path: Path,
        show_progress: bool = True,
    ) -> VideoFile:
        """
        Create a video with subtitles from TTS metadata JSON.

        Args:
            tts_metadata_json: Path to audio_script.json with timing metadata
            video_config: Video configuration including subtitle settings
            output_path: Path where the video should be saved
            show_progress: Whether to display progress during video creation

        Returns:
            VideoFile representing the created video with subtitles
        """
        # Load TTS metadata
        metadata = self.metadata_writer.load_audio_script_metadata(tts_metadata_json)
        
        # Reconstruct AudioScript from metadata
        audio_script = self._create_audio_script_from_metadata(metadata)
        
        # Create character scenes from metadata
        character_scenes = []
        
        for audio_data in metadata["audio_files"]:
            char_data = audio_data["character"]
            audio_meta = audio_data["audio_metadata"]
            
            # Reconstruct Character
            character = Character(
                name=char_data["name"],
                speaking_style=char_data["speaking_style"],
                conversational_role=char_data["conversational_role"],
                image_path=Path(char_data["image_path"]) if char_data["image_path"] else Path(""),
                tts_voice_clone=char_data["tts_voice_clone"],
                tts_voice_predefined=char_data["tts_voice_predefined"],
                tts_voice_profile=char_data["tts_voice_profile"],
                tts_voice_profile_overrides=char_data["tts_voice_profile_overrides"],
            )
            
            # Reconstruct AudioFile
            audio_file = AudioFile(
                path=Path(audio_meta["full_path"]),
                character=character,
                dialogue=audio_data["dialogue"],
                duration_seconds=audio_meta["duration_seconds"],
                file_size_bytes=audio_meta["file_size_bytes"],
            )
            
            # Create scene with timing from metadata
            scene = CharacterScene(
                character=character,
                audio_file=audio_file,
                start_time=audio_meta["start_time"],
                duration=audio_meta["duration_seconds"],
                character_image=character.image_path if character.image_path.exists() else None,
            )
            character_scenes.append(scene)

        # Create video project with subtitle support
        video_project = VideoProject(
            background_clip=VideoClip(path=video_config.background_video),
            character_scenes=character_scenes,
            enable_subtitles=True,  # Enable subtitles for this use case
        )

        # Create MoviePy client and generate video
        moviepy_config = video_config.get_provider_config()
        client = MoviePyVideoClient(moviepy_config)
        
        return client.create_video_with_subtitles(
            project=video_project,
            audio_script=audio_script,
            output_path=output_path,
            show_progress=show_progress,
        )

    def execute_from_config(
        self,
        tts_metadata_json: Path,
        config_path: Path,
        output_filename: Optional[str] = None,
        show_progress: bool = True,
    ) -> VideoFile:
        """
        Create a video with subtitles using configuration file and TTS metadata JSON.

        Args:
            tts_metadata_json: Path to audio_script.json with timing metadata
            config_path: Path to JSON configuration file
            output_filename: Optional custom filename for output video
            show_progress: Whether to display progress during video creation

        Returns:
            VideoFile representing the created video with subtitles
        """
        # Load configuration
        project_config = ConfigurationLoader.load_from_file(config_path)

        if not project_config.video_config:
            raise ValueError("Video configuration is required for subtitle video creation")

        # Set up output paths
        project_dir = project_config.base_output_dir / project_config.project_name
        if output_filename:
            video_output_path = project_dir / "videos" / output_filename
        else:
            video_output_path = (
                project_dir / "videos" / f"{project_config.project_name}_from_metadata.mp4"
            )

        return self.execute(
            tts_metadata_json=tts_metadata_json,
            video_config=project_config.video_config,
            output_path=video_output_path,
            show_progress=show_progress,
        )

    def _create_audio_script_from_metadata(self, metadata: dict) -> AudioScript:
        """Reconstruct AudioScript from metadata dictionary."""
        audio_script = AudioScript()
        audio_script.total_duration_seconds = metadata["total_duration_seconds"]
        
        for audio_data in metadata["audio_files"]:
            char_data = audio_data["character"]
            audio_meta = audio_data["audio_metadata"]
            
            # Reconstruct Character
            character = Character(
                name=char_data["name"],
                speaking_style=char_data["speaking_style"],
                conversational_role=char_data["conversational_role"],
                image_path=Path(char_data["image_path"]) if char_data["image_path"] else Path(""),
                tts_voice_clone=char_data["tts_voice_clone"],
                tts_voice_predefined=char_data["tts_voice_predefined"],
                tts_voice_profile=char_data["tts_voice_profile"],
                tts_voice_profile_overrides=char_data["tts_voice_profile_overrides"],
            )
            
            # Reconstruct AudioFile
            audio_file = AudioFile(
                path=Path(audio_meta["full_path"]),
                character=character,
                dialogue=audio_data["dialogue"],
                duration_seconds=audio_meta["duration_seconds"],
                file_size_bytes=audio_meta["file_size_bytes"],
            )
            
            audio_script.add_audio_file(audio_file)
        
        return audio_script


def main():
    """Main function demonstrating subtitle video creation from TTS metadata."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) not in [3, 4]:
        print(
            "Usage: python create_video_from_tts_metadata_use_case.py <tts_metadata_json> <config_file> [output_filename]"
        )
        print("       tts_metadata_json: Path to audio_script.json from TTS generation")
        print("       output_filename: Optional custom filename for the output video")
        sys.exit(1)

    tts_metadata_json = Path(sys.argv[1])
    config_path = Path(sys.argv[2])
    output_filename = sys.argv[3] if len(sys.argv) > 3 else None

    if not tts_metadata_json.exists():
        print(f"Error: TTS metadata JSON not found: {tts_metadata_json}")
        sys.exit(1)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Load config to get project info
        project_config = ConfigurationLoader.load_from_file(config_path)

        # Create video with subtitles from metadata
        use_case = CreateVideoFromTTSMetadataUseCase()
        video_file = use_case.execute_from_config(
            tts_metadata_json=tts_metadata_json,
            config_path=config_path,
            output_filename=output_filename,
            show_progress=True,
        )

        # Load metadata for reporting
        metadata = use_case.metadata_writer.load_audio_script_metadata(tts_metadata_json)

        print(f"Video Creation from TTS Metadata Results for: {project_config.project_name}")
        print("=" * 60)

        print(f"✓ Processed {len(metadata['audio_files'])} audio files from metadata")
        print(f"✓ Total audio duration: {metadata['total_duration_seconds']:.2f} seconds")

        character_names = set(audio["character"]["name"] for audio in metadata["audio_files"])
        print(f"✓ Characters: {', '.join(character_names)}")

        print("\n🔊 Audio Files (from metadata):")
        for audio_data in metadata["audio_files"]:
            char_name = audio_data["character"]["name"]
            dialogue = audio_data["dialogue"]
            duration = audio_data["audio_metadata"]["duration_seconds"]
            print(f"  - {char_name} ({duration:.1f}s): {dialogue[:50]}...")

        print("\n🎬 Video with Subtitles:")
        print(f"  - {video_file.path.name}")
        print(f"  - Size: {video_file.file_size_bytes / 1024 / 1024:.2f} MB")
        if video_file.render_time_seconds:
            print(f"  - Render time: {video_file.render_time_seconds:.2f} seconds")

        print(f"\n📁 Output saved to: {video_file.path}")

    except Exception as e:
        print(f"Error creating video from TTS metadata: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()