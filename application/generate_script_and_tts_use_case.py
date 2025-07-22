from pathlib import Path

from config.domain.models import ProjectConfig
from config.infrastructure.json import ConfigurationLoader
from script.application.generate_script_use_case import ScriptGenerationUseCase
from tts.application.generate_speech_from_entries_use_case import (
    GenerateSpeechFromEntriesUseCase,
)
from tts.application.merge_audio_script_use_case import MergeAudioScriptUseCase
from tts.domain.models import AudioScript, AudioFile
from script.domain.models import ScriptEntry
from typing import List, Optional
from typing import Tuple


class GenerateScriptAndTTSUseCase:
    """Orchestrating use case that generates script and converts it to TTS audio."""

    def __init__(self):
        self.script_use_case = ScriptGenerationUseCase()
        self.tts_use_case = GenerateSpeechFromEntriesUseCase()
        self.merge_use_case = MergeAudioScriptUseCase()

    def execute(
        self,
        project_config: ProjectConfig,
        merge_audio: bool = True,
        delay_between_files: float = 0.0,
    ) -> Tuple[List[ScriptEntry], AudioScript, Optional[AudioFile]]:
        """
        Generate script and TTS audio from project configuration.

        Args:
            project_config: Complete project configuration
            merge_audio: Whether to merge individual audio files into one file
            delay_between_files: Seconds of silence between merged audio files

        Returns:
            Tuple of (script_entries, audio_script, merged_audio_file)
        """
        # Validate required configurations
        if not project_config.script_config:
            raise ValueError("Script configuration is required")
        if not project_config.tts_config:
            raise ValueError("TTS configuration is required")

        # Construct output directories
        project_dir = project_config.base_output_dir / project_config.project_name
        script_output_dir = project_dir / "scripts"
        tts_output_dir = project_dir / "tts"

        # Step 1: Generate script
        script_entries = self.script_use_case.execute_and_save(
            script_config=project_config.script_config,
            output_dir=script_output_dir,
        )

        # Step 2: Generate TTS from script
        speech_script = self.tts_use_case.execute(
            script_entries=script_entries,
            tts_config=project_config.tts_config,
            output_dir=tts_output_dir,
        )

        # Step 3: Optionally merge audio files
        merged_audio_file = None
        if merge_audio and speech_script.audio_files:
            merged_output_path = (
                project_dir / f"{project_config.project_name}_merged.wav"
            )
            merged_audio_file = self.merge_use_case.execute(
                audio_script=speech_script,
                output_path=merged_output_path,
                delay_between_files=delay_between_files,
                show_progress=True,
            )

        # Create summary file
        summary_file = project_dir / f"{project_config.project_name}_summary.txt"
        self._create_summary_file(
            summary_file, script_entries, speech_script, merged_audio_file
        )

        return script_entries, speech_script, merged_audio_file

    def _create_summary_file(
        self,
        summary_file: Path,
        script_entries,
        speech_script,
        merged_audio_file: Optional[AudioFile] = None,
    ) -> None:
        """Create a summary file with generation results."""
        characters = list(set(entry.character.name for entry in script_entries))

        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("# Script and TTS Generation Summary\n\n")
            f.write(f"Generated: {len(script_entries)} script entries\n")
            f.write(f"Audio Files: {len(speech_script.audio_files)}\n")
            f.write(
                f"Total Duration: {speech_script.total_duration_seconds:.2f} seconds\n"
            )
            f.write(f"Characters: {', '.join(characters)}\n\n")

            f.write("## TTS Files\n")
            for audio_file in speech_script.audio_files:
                filename = audio_file.path.name
                f.write(f"- {filename}\n")

            assert merged_audio_file is not None, (
                "Merged audio file should not be None if merge_audio is True"
            )
            assert merged_audio_file.path is not None, (
                "Merged audio file path should not be None"
            )
            assert merged_audio_file.duration_seconds is not None, (
                "Merged audio file duration should not be None"
            )
            assert merged_audio_file.file_size_bytes is not None, (
                "Merged audio file size should not be None"
            )

            if merged_audio_file:
                f.write(f"\n## Merged Audio\n")
                f.write(f"- {merged_audio_file.path.name}\n")
                f.write(
                    f"- Total Duration: {merged_audio_file.duration_seconds:.2f} seconds\n"
                )
                f.write(
                    f"- File Size: {merged_audio_file.file_size_bytes / 1024 / 1024:.2f} MB\n"
                )

    def execute_and_save_all(
        self,
        config_path: Path,
        merge_audio: bool = True,
        delay_between_files: float = 0.0,
    ) -> Tuple[List[ScriptEntry], AudioScript, Optional[AudioFile]]:
        """
        Generate script and TTS with comprehensive output files and metadata.

        Args:
            config_path: Path to JSON configuration file
            merge_audio: Whether to merge individual audio files into one file
            delay_between_files: Seconds of silence between merged audio files

        Returns:
            Tuple of (script_entries, audio_script, merged_audio_file)
        """
        # Override the base output dir from config with the provided one
        project_config = ConfigurationLoader.load_from_file(config_path)

        return self.execute(project_config, merge_audio, delay_between_files)


def main():
    """Main function demonstrating script and TTS generation."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) != 2:
        print("Usage: python generate_script_and_tts_use_case.py <config_file>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Load config to get project info
        project_config = ConfigurationLoader.load_from_file(config_path)

        use_case = GenerateScriptAndTTSUseCase()
        script_entries, speech_script, merged_audio = use_case.execute_and_save_all(
            config_path
        )

        print(f"Script and TTS Generation Results for: {project_config.project_name}")
        print("=" * 60)

        print(f"✓ Generated {len(script_entries)} script entries")
        print(f"✓ Generated {len(speech_script.audio_files)} audio files")
        print(f"✓ Total duration: {speech_script.total_duration_seconds:.2f} seconds")

        characters = list(set(entry.character.name for entry in script_entries))
        print(f"✓ Characters: {', '.join(characters)}")

        # Show output directories
        project_dir = project_config.base_output_dir / project_config.project_name
        summary_file = project_dir / f"{project_config.project_name}_summary.txt"
        script_dir = project_dir / "scripts"

        print(f"\n📄 Summary file: {summary_file}")
        print(f"\n📝 Script Directory: {script_dir}")

        print("\n🔊 TTS Files:")
        for audio_file in speech_script.audio_files:
            print(f"  - {audio_file.path.name}")

        assert merged_audio is not None, "merged_audio should not be None"
        assert merged_audio.file_size_bytes is not None, (
            "Merged audio file size should not be None"
        )

        if merged_audio:
            print("\n🎵 Merged Audio:")
            print(f"  - {merged_audio.path.name}")
            print(f"  - Duration: {merged_audio.duration_seconds:.2f} seconds")
            print(f"  - Size: {merged_audio.file_size_bytes / 1024 / 1024:.2f} MB")

        print("\n🎭 Generated Dialogue Preview:")
        print("-" * 40)

        # Show first 3 script entries
        for i, entry in enumerate(script_entries[:3], 1):
            print(f"{i}. {entry.character.name}: {entry.content}")

        if len(script_entries) > 3:
            print(f"... and {len(script_entries) - 3} more entries")

    except Exception as e:
        print(f"Error generating script and TTS: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
