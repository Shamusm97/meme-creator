"""Refactored use case for loading existing audio files into an AudioScript."""

from pathlib import Path
from typing import List, Optional

from tts.domain.models import AudioScript
from config.domain.models import Character
from tts.infrastructure.audio_script_repository import AudioScriptRepository


class LoadAudioScriptUseCase:
    """Use case for loading existing audio files into an AudioScript."""

    def __init__(self, audio_script_repository: AudioScriptRepository | None = None):
        self.audio_script_repository = (
            audio_script_repository or AudioScriptRepository()
        )

    def execute(
        self, audio_dir: Path, characters: Optional[List[Character]] = None
    ) -> AudioScript:
        """
        Load audio files from a directory into an AudioScript.

        Args:
            audio_dir: Directory containing audio files
            characters: Optional list of characters to match with audio files

        Returns:
            AudioScript with loaded audio files
        """
        return self.audio_script_repository.load_audio_script_from_directory(
            audio_dir, characters
        )

    def execute_from_project_dir(self, project_dir: Path) -> AudioScript:
        """
        Load audio files from a project directory structure.

        Args:
            project_dir: Project directory containing tts/ subdirectory

        Returns:
            AudioScript with loaded audio files
        """
        tts_dir = project_dir / "tts"
        return self.execute(tts_dir)


def main():
    """Main function demonstrating audio script loading."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) != 2:
        print("Usage: python load_audio_script_use_case.py <audio_directory>")
        sys.exit(1)

    audio_dir = Path(sys.argv[1])
    if not audio_dir.exists():
        print(f"Error: Audio directory not found: {audio_dir}")
        sys.exit(1)

    try:
        use_case = LoadAudioScriptUseCase()
        audio_script = use_case.execute(audio_dir)

        print(f"Loaded Audio Script from: {audio_dir}")
        print("=" * 50)

        print(f"✓ Loaded {len(audio_script.audio_files)} audio files")
        print(f"✓ Total duration: {audio_script.total_duration_seconds:.2f} seconds")

        characters = audio_script.get_characters()
        character_names = [char.name for char in characters]
        print(f"✓ Characters: {', '.join(character_names)}")

        print("\n🔊 Audio Files:")
        for audio_file in audio_script.audio_files:
            print(f"  - {audio_file.path.name} ({audio_file.duration_seconds:.1f}s)")

        print("\n🎭 Audio Content Preview:")
        print("-" * 40)

        # Show first 3 audio files
        for i, audio_file in enumerate(audio_script.audio_files[:3], 1):
            print(f"{i}. {audio_file.character.name}: {audio_file.dialogue}")

        if len(audio_script.audio_files) > 3:
            print(f"... and {len(audio_script.audio_files) - 3} more files")

    except Exception as e:
        print(f"Error loading audio script: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

