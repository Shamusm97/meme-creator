"""Unified use case for generating complete audio script from project directory."""

from pathlib import Path
import json
from typing import List

from config.domain.models import Character
from script.domain.models import ScriptEntry, Script
from tts.domain.models import AudioScript
from tts.infrastructure.audio_script_repository import AudioScriptRepository


class GenerateCompleteAudioScriptUseCase:
    """
    Unified use case that reads script_entries.json and generates enhanced audio_script.json.
    
    This combines script parsing with audio file discovery to create comprehensive metadata.
    """

    def __init__(self, audio_script_repository: AudioScriptRepository = None):
        self.audio_script_repository = audio_script_repository or AudioScriptRepository()

    def execute(self, project_dir: Path) -> AudioScript:
        """
        Generate complete audio script from project directory structure.

        Expected structure:
        project_dir/
        ├── scripts/
        │   └── script_entries.json
        ├── tts/
        │   ├── 000_character1.wav
        │   ├── 001_character2.wav
        │   └── ...
        └── audio_script.json (output)

        Args:
            project_dir: Project root directory

        Returns:
            AudioScript with enhanced metadata
        """
        # Validate project structure
        scripts_dir = project_dir / "scripts"
        tts_dir = project_dir / "tts"
        script_entries_file = scripts_dir / "script_entries.json"

        if not script_entries_file.exists():
            raise FileNotFoundError(f"Script entries file not found: {script_entries_file}")
        
        if not tts_dir.exists():
            raise FileNotFoundError(f"TTS directory not found: {tts_dir}")

        # Load script entries and extract characters/content
        script_entries, characters = self._load_script_entries_and_characters(script_entries_file)
        
        print(f"📖 Loaded {len(script_entries)} script entries")
        print(f"🎭 Found {len(characters)} unique characters")

        # Load audio files using characters for better mapping
        audio_script = self.audio_script_repository.load_audio_script_from_directory(
            tts_dir, characters
        )

        # Enhance audio script with script content
        enhanced_audio_script = self._enhance_audio_script_with_content(
            audio_script, script_entries
        )

        # Save enhanced metadata
        output_json = project_dir / "audio_script.json"
        self.audio_script_repository.save_audio_script_metadata(
            enhanced_audio_script, output_json
        )

        print(f"✅ Generated complete audio script: {output_json}")
        print(f"📊 Total duration: {enhanced_audio_script.total_duration_seconds:.2f} seconds")

        return enhanced_audio_script

    def _load_script_entries_and_characters(self, script_entries_file: Path) -> tuple[List[ScriptEntry], List[Character]]:
        """Load script entries and extract unique characters."""
        with open(script_entries_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        script_entries = []
        characters_map = {}

        for entry_data in data:
            # Load character
            char_data = entry_data["character"]
            character = Character(
                name=char_data["name"],
                speaking_style=char_data.get("speaking_style", ""),
                conversational_role=char_data.get("conversational_role", ""),
                image_path=Path(char_data.get("image_path", "")) if char_data.get("image_path") else None,
                tts_voice_clone=char_data.get("tts_voice_clone", ""),
                tts_voice_predefined=char_data.get("tts_voice_predefined", ""),
                tts_voice_profile=char_data.get("tts_voice_profile", ""),
                tts_voice_profile_overrides=char_data.get("tts_voice_profile_overrides", {}),
            )

            # Store unique characters
            characters_map[character.name.lower()] = character

            # Create script entry
            script_entry = ScriptEntry(
                character=character,
                content=entry_data["content"]
            )
            script_entries.append(script_entry)

        characters = list(characters_map.values())
        return script_entries, characters

    def _enhance_audio_script_with_content(
        self, audio_script: AudioScript, script_entries: List[ScriptEntry]
    ) -> AudioScript:
        """
        Enhance audio script by matching audio files with actual script content.
        
        Assumes audio files are named with index prefixes (000_character.wav, 001_character.wav)
        that correspond to script entry order.
        """
        enhanced_audio_script = AudioScript()

        for i, audio_file in enumerate(audio_script.audio_files):
            # Try to match with script entry by index
            if i < len(script_entries):
                script_entry = script_entries[i]
                
                # Update audio file with actual dialogue content
                from tts.domain.models import AudioFile
                enhanced_audio_file = AudioFile(
                    path=audio_file.path,
                    character=script_entry.character,  # Use character from script (more complete)
                    dialogue=script_entry.content,     # Use actual dialogue content
                    duration_seconds=audio_file.duration_seconds,
                    file_size_bytes=audio_file.file_size_bytes,
                )
                
                enhanced_audio_script.add_audio_file(enhanced_audio_file)
                
                print(f"🔗 Linked {audio_file.path.name} → {script_entry.character.name}: {script_entry.content[:50]}...")
            else:
                # Keep original if no matching script entry
                enhanced_audio_script.add_audio_file(audio_file)
                print(f"⚠️  No script match for {audio_file.path.name}")

        return enhanced_audio_script


def main():
    """Main function demonstrating complete audio script generation."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) != 2:
        print("Usage: python generate_complete_audio_script_use_case.py <project_directory>")
        print("\nExpected project structure:")
        print("project_dir/")
        print("├── scripts/")
        print("│   └── script_entries.json")
        print("├── tts/")
        print("│   ├── 000_character1.wav")
        print("│   ├── 001_character2.wav")
        print("│   └── ...")
        print("└── audio_script.json (output)")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    try:
        use_case = GenerateCompleteAudioScriptUseCase()
        audio_script = use_case.execute(project_dir)

        print(f"\n🎉 Complete Audio Script Generation Results")
        print("=" * 50)
        print(f"✅ Project: {project_dir.name}")
        print(f"📁 Audio files: {len(audio_script.audio_files)}")
        print(f"⏱️  Total duration: {audio_script.total_duration_seconds:.2f} seconds")
        
        characters = audio_script.get_characters()
        character_names = [char.name for char in characters]
        print(f"🎭 Characters: {', '.join(character_names)}")
        
        print(f"💾 Enhanced metadata: {project_dir / 'audio_script.json'}")

        print("\n📋 Content Preview:")
        print("-" * 30)
        for i, audio_file in enumerate(audio_script.audio_files[:3], 1):
            print(f"{i}. {audio_file.character.name}: {audio_file.dialogue[:80]}...")

        if len(audio_script.audio_files) > 3:
            print(f"... and {len(audio_script.audio_files) - 3} more entries")

    except Exception as e:
        print(f"Error generating complete audio script: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()