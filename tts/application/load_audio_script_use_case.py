from pathlib import Path
from typing import List, Optional
import json

from tts.domain.models import AudioScript, AudioFile
from config.domain.models import Character


class LoadAudioScriptUseCase:
    """Use case for loading existing audio files into an AudioScript."""

    def execute(self, audio_dir: Path, characters: Optional[List[Character]] = None) -> AudioScript:
        """
        Load audio files from a directory into an AudioScript.

        Args:
            audio_dir: Directory containing audio files
            characters: Optional list of characters to match with audio files

        Returns:
            AudioScript with loaded audio files
        """
        if not audio_dir.exists() or not audio_dir.is_dir():
            raise ValueError(f"Audio directory does not exist: {audio_dir}")

        # Find all audio files in the directory
        audio_extensions = {'.wav', '.mp3', '.opus', '.m4a', '.aac', '.flac'}
        audio_files = []
        
        for file_path in sorted(audio_dir.iterdir()):
            if file_path.suffix.lower() in audio_extensions:
                audio_files.append(file_path)

        if not audio_files:
            raise ValueError(f"No audio files found in directory: {audio_dir}")

        # Try to load character mapping from script_entries.json if it exists
        script_entries_file = audio_dir.parent / "scripts" / "script_entries.json"
        character_mapping = self._load_character_mapping(script_entries_file, characters)

        # Create AudioScript
        audio_script = AudioScript()

        for audio_file_path in audio_files:
            # Extract character info from filename or use default
            character = self._determine_character(audio_file_path, character_mapping, characters)
            
            # Extract dialogue from filename (remove index prefix and extension)
            dialogue = self._extract_dialogue_from_filename(audio_file_path)

            # Estimate duration (will be more accurate when file is actually loaded)
            estimated_duration = self._estimate_audio_duration(audio_file_path)

            # Get file size
            file_size = audio_file_path.stat().st_size

            # Create AudioFile
            audio_file = AudioFile(
                path=audio_file_path,
                character=character,
                dialogue=dialogue,
                duration_seconds=estimated_duration,
                file_size_bytes=file_size,
            )

            audio_script.add_audio_file(audio_file)

        return audio_script

    def _load_character_mapping(
        self, script_entries_file: Path, characters: Optional[List[Character]]
    ) -> dict:
        """Load character mapping from script_entries.json if available."""
        character_mapping = {}
        
        if script_entries_file.exists():
            try:
                with open(script_entries_file, 'r', encoding='utf-8') as f:
                    script_data = json.load(f)
                
                for entry in script_data:
                    if 'character' in entry and 'name' in entry['character']:
                        char_name = entry['character']['name'].lower()
                        character_mapping[char_name] = Character(
                            name=entry['character']['name'],
                            speaking_style=entry['character'].get('speaking_style', 'neutral'),
                            conversational_role=entry['character'].get('conversational_role', 'participant'),
                            image_path=Path(entry['character']['image_path']) if entry['character'].get('image_path') else None,
                            tts_voice_clone=entry['character'].get('tts_voice_clone', ''),
                            tts_voice_predefined=entry['character'].get('tts_voice_predefined', ''),
                            tts_voice_profile=entry['character'].get('tts_voice_profile', 'STANDARD_NARRATION'),
                            tts_voice_profile_overrides=entry['character'].get('tts_voice_profile_overrides', {}),
                        )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Could not load character mapping from {script_entries_file}: {e}")

        return character_mapping

    def _determine_character(
        self, 
        audio_file_path: Path, 
        character_mapping: dict, 
        characters: Optional[List[Character]]
    ) -> Character:
        """Determine character from filename or provided characters."""
        filename = audio_file_path.stem.lower()
        
        # Remove index prefix (e.g., "000_peter" -> "peter")
        if '_' in filename:
            parts = filename.split('_', 1)
            if parts[0].isdigit():
                filename = parts[1]

        # Try to match with character mapping first
        if filename in character_mapping:
            return character_mapping[filename]

        # Try to match with provided characters
        if characters:
            for character in characters:
                if character.name.lower() == filename:
                    return character

        # Create a default character if no match found
        return Character(
            name=filename.title(),
            speaking_style="neutral",
            conversational_role="participant",
        )

    def _extract_dialogue_from_filename(self, audio_file_path: Path) -> str:
        """Extract dialogue text from filename."""
        # This is a simple implementation - in practice, you might want to
        # store dialogue separately or use a more sophisticated naming scheme
        filename = audio_file_path.stem
        
        # Remove index prefix
        if '_' in filename:
            parts = filename.split('_', 1)
            if parts[0].isdigit():
                filename = parts[1]

        # Use filename as dialogue placeholder
        return f"Audio content from {filename}"

    def _estimate_audio_duration(self, audio_file_path: Path) -> float:
        """Estimate audio duration based on file size (rough approximation)."""
        try:
            # Try to use actual audio library if available
            try:
                import librosa
                duration = librosa.get_duration(path=str(audio_file_path))
                return duration
            except ImportError:
                pass

            try:
                import wave
                if audio_file_path.suffix.lower() == '.wav':
                    with wave.open(str(audio_file_path), 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        sample_rate = wav_file.getframerate()
                        return frames / float(sample_rate)
            except ImportError:
                pass

            # Fallback: rough estimation based on file size
            # Assume ~128kbps compression for MP3/similar formats
            file_size_mb = audio_file_path.stat().st_size / (1024 * 1024)
            estimated_duration = file_size_mb * 60  # Very rough estimate
            return max(1.0, estimated_duration)  # At least 1 second
            
        except Exception:
            # If all else fails, return a default duration
            return 3.0

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