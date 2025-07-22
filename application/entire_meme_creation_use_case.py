from pathlib import Path
from typing import List, Optional, Tuple

from config.domain.models import ProjectConfig
from config.infrastructure.json import ConfigurationLoader
from script.application.generate_script_use_case import ScriptGenerationUseCase
from tts.application.merge_audio_script_use_case import MergeAudioScriptUseCase
from tts.application.generate_audio_script_from_script_entries_use_case import (
    GenerateAudioScriptFromScriptEntriesUseCase,
)
from video.application.create_video_use_case import CreateVideoUseCase
from script.domain.models import ScriptEntry
from tts.domain.models import AudioScript, AudioFile
from video.domain.models import VideoFile


class MemeCreationUseCase:
    """Orchestrates the complete meme creation workflow."""

    def __init__(self):
        self.script_use_case = ScriptGenerationUseCase()
        self.tts_use_case = GenerateAudioScriptFromScriptEntriesUseCase()
        self.merge_use_case = MergeAudioScriptUseCase()
        self.video_use_case = CreateVideoUseCase()

    def execute(
        self,
        project_config: ProjectConfig,
        merge_audio: bool = True,
        delay_between_files: float = 0.0,
    ) -> Tuple[List[ScriptEntry], AudioScript, Optional[AudioFile], VideoFile]:
        """
        Execute the complete meme creation workflow.

        Args:
            project_config: Complete project configuration
            merge_audio: Whether to merge individual audio files into one file
            delay_between_files: Seconds of silence between merged audio files

        Returns:
            Tuple of (script_entries, audio_script, merged_audio_file, video_file)
        """
        # Validate required configurations
        if not project_config.script_config:
            raise ValueError("Script configuration is required")
        if not project_config.tts_config:
            raise ValueError("TTS configuration is required")
        if not project_config.video_config:
            raise ValueError("Video configuration is required")

        # Construct output directories
        project_dir = project_config.base_output_dir / project_config.project_name
        script_output_dir = project_dir / "scripts"
        tts_output_dir = project_dir / "tts"
        video_output_dir = project_dir / "videos"

        # Step 1: Generate script
        script = self.script_use_case.execute_and_save(
            script_config=project_config.script_config,
            output_dir=script_output_dir,
        )

        # Step 2: Generate TTS from script
        audio_script = self.tts_use_case.execute(
            script_entries=script.entries,
            tts_config=project_config.tts_config,
            output_dir=tts_output_dir,
        )

        # Step 3: Optionally merge audio files
        merged_audio_file = None
        if merge_audio and audio_script.audio_files:
            merged_output_path = (
                project_dir / f"{project_config.project_name}_merged.wav"
            )
            merged_audio_file = self.merge_use_case.execute(
                audio_script=audio_script,
                output_path=merged_output_path,
                delay_between_files=delay_between_files,
                show_progress=True,
            )

        # Step 4: Create video with subtitles from TTS metadata
        video_output_path = video_output_dir / f"{project_config.project_name}_meme.mp4"
        tts_metadata_json = tts_output_dir / "audio_script.json"
        video_file = self.video_use_case.execute(
            audio_script=audio_script,
            video_config=project_config.video_config,
            output_path=video_output_path,
            show_progress=True,
        )

        # Create summary file
        summary_file = project_dir / f"{project_config.project_name}_meme_summary.txt"
        self._create_summary_file(
            summary_file, script.entries, audio_script, merged_audio_file, video_file
        )

        return script.entries, audio_script, merged_audio_file, video_file

    def _create_summary_file(
        self,
        summary_file: Path,
        script_entries: List[ScriptEntry],
        audio_script: AudioScript,
        merged_audio_file: Optional[AudioFile],
        video_file: VideoFile,
    ) -> None:
        """Create a summary file with generation results."""
        characters = list(set(entry.character.name for entry in script_entries))

        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("# Complete Meme Creation Summary\n\n")
            f.write(f"Generated: {len(script_entries)} script entries\n")
            f.write(f"Audio Files: {len(audio_script.audio_files)}\n")
            f.write(
                f"Total Duration: {audio_script.total_duration_seconds:.2f} seconds\n"
            )
            f.write(f"Characters: {', '.join(characters)}\n\n")

            f.write("## Script Files\n")
            f.write("- script_entries.json\n\n")

            f.write("## TTS Files\n")
            for audio_file in audio_script.audio_files:
                filename = audio_file.path.name
                f.write(f"- {filename}\n")

            if merged_audio_file:
                f.write(f"\n## Merged Audio\n")
                f.write(f"- {merged_audio_file.path.name}\n")
                f.write(
                    f"- Total Duration: {merged_audio_file.duration_seconds:.2f} seconds\n"
                )
                f.write(
                    f"- File Size: {merged_audio_file.file_size_bytes / 1024 / 1024:.2f} MB\n"
                )

            f.write(f"\n## Video (with Subtitles)\n")
            f.write(f"- {video_file.path.name}\n")
            f.write(f"- File Size: {video_file.file_size_bytes / 1024 / 1024:.2f} MB\n")
            if video_file.render_time_seconds:
                f.write(
                    f"- Render Time: {video_file.render_time_seconds:.2f} seconds\n"
                )
            f.write(f"\n## TTS Metadata\n")
            f.write(f"- audio_script.json (timing + metadata for subtitles)\n")

    def execute_and_save_all(
        self,
        config_path: Path,
        merge_audio: bool = True,
        delay_between_files: float = 0.0,
    ) -> Tuple[List[ScriptEntry], AudioScript, Optional[AudioFile], VideoFile]:
        """
        Execute complete meme creation with comprehensive output files and metadata.

        Args:
            config_path: Path to JSON configuration file
            merge_audio: Whether to merge individual audio files into one file
            delay_between_files: Seconds of silence between merged audio files

        Returns:
            Tuple of (script_entries, audio_script, merged_audio_file, video_file)
        """
        project_config = ConfigurationLoader.load_from_file(config_path)
        return self.execute(project_config, merge_audio, delay_between_files)


def main():
    """Main function demonstrating the complete workflow."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) != 2:
        print("Usage: python meme_creation_use_case.py <config_file>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Load config to get project info
        project_config = ConfigurationLoader.load_from_file(config_path)

        use_case = MemeCreationUseCase()
        script_entries, audio_script, merged_audio, video_file = (
            use_case.execute_and_save_all(config_path)
        )

        print(f"Complete Meme Creation Results for: {project_config.project_name}")
        print("=" * 60)

        print(f"✓ Generated {len(script_entries)} script entries")
        print(f"✓ Generated {len(audio_script.audio_files)} audio files")
        print(f"✓ Total duration: {audio_script.total_duration_seconds:.2f} seconds")

        characters = list(set(entry.character.name for entry in script_entries))
        print(f"✓ Characters: {', '.join(characters)}")

        # Show output directories
        project_dir = project_config.base_output_dir / project_config.project_name
        summary_file = project_dir / f"{project_config.project_name}_meme_summary.txt"

        print(f"\n📄 Summary file: {summary_file}")

        print("\n🔊 TTS Files:")
        for audio_file in audio_script.audio_files:
            print(f"  - {audio_file.path.name}")

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

        print("\n🎭 Generated Dialogue Preview:")
        print("-" * 40)

        # Show first 3 script entries
        for i, entry in enumerate(script_entries[:3], 1):
            print(f"{i}. {entry.character.name}: {entry.content}")

        if len(script_entries) > 3:
            print(f"... and {len(script_entries) - 3} more entries")

    except Exception as e:
        print(f"Error creating meme: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
