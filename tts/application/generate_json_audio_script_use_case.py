"""Use case for generating audio script JSON metadata from existing audio files."""

from pathlib import Path
from typing import List, Optional

from config.domain.models import Character
from tts.domain.models import AudioScript
from tts.infrastructure.audio_script_repository import AudioScriptRepository


class GenerateAudioScriptJsonUseCase:
    """Use case for creating JSON metadata from existing audio files in a directory."""

    def __init__(self, audio_script_repository: AudioScriptRepository | None = None):
        self.audio_script_repository = (
            audio_script_repository or AudioScriptRepository()
        )

    def execute(
        self,
        audio_dir: Path,
        output_json_path: Path,
        characters: Optional[List[Character]] = None,
    ) -> AudioScript:
        """
        Generate JSON metadata from audio files in a directory.

        Args:
            audio_dir: Directory containing audio files
            output_json_path: Path where to save the JSON metadata
            characters: Optional list of characters for mapping

        Returns:
            AudioScript that was created from the directory
        """
        # Load audio files from directory
        audio_script = self.audio_script_repository.load_audio_script_from_directory(
            audio_dir, characters
        )

        # Save metadata JSON
        self.audio_script_repository.save_audio_script_metadata(
            audio_script, output_json_path
        )

        return audio_script

    def execute_with_default_output(
        self,
        audio_dir: Path,
        characters: Optional[List[Character]] = None,
    ) -> AudioScript:
        """
        Generate JSON metadata with default output location (audio_script.json in same directory).

        Args:
            audio_dir: Directory containing audio files
            characters: Optional list of characters for mapping

        Returns:
            AudioScript that was created from the directory
        """
        output_json_path = audio_dir / "audio_script.json"
        return self.execute(audio_dir, output_json_path, characters)


def main():
    """Main function demonstrating JSON generation from audio files."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 2:
        print(
            "Usage: python generate_audio_script_json_use_case.py <audio_directory> [output_json]"
        )
        print("       python generate_audio_script_json_use_case.py <audio_directory>")
        print(
            "If output_json is not specified, saves to 'audio_script.json' in the audio directory"
        )
        sys.exit(1)

    audio_dir = Path(sys.argv[1])
    output_json = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else audio_dir / "audio_script.json"
    )

    if not audio_dir.exists():
        print(f"Error: Audio directory not found: {audio_dir}")
        sys.exit(1)

    try:
        use_case = GenerateAudioScriptJsonUseCase()
        audio_script = use_case.execute(audio_dir, output_json)

        print(f"Audio Script JSON Generation Results")
        print("=" * 40)
        print(f"✓ Processed {len(audio_script.audio_files)} audio files")
        print(f"✓ Total duration: {audio_script.total_duration_seconds:.2f} seconds")

        characters = audio_script.get_characters()
        character_names = [char.name for char in characters]
        print(f"✓ Characters: {', '.join(character_names)}")
        print(f"✓ JSON metadata saved to: {output_json}")

        print("\n🔊 Audio Files Processed:")
        for audio_file in audio_script.audio_files:
            print(
                f"  - {audio_file.path.name} ({audio_file.duration_seconds or 0:.1f}s)"
            )

    except Exception as e:
        print(f"Error generating audio script JSON: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

