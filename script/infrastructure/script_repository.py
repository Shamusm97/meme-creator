from pathlib import Path
from typing import List
import json

from config.domain.models import Character
from script.domain.models import Script, ScriptEntry


class ScriptRepository:
    """Repository for loading and saving scripts from/to files."""

    def load_from_formatted_txt_file(
        self, file_path: Path, characters: List[Character]
    ) -> Script:
        """
        Load script entries from a dialogue text file.

        Format expected:
        CHARACTER_NAME: dialogue text
        ANOTHER_CHARACTER: more dialogue

        Args:
            file_path: Path to dialogue file
            characters: List of available characters for matching

        Returns:
            List of script entries, wrapped in a Script object
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Dialogue file not found: {file_path}")

        script_entries = []
        character_map = {char.name.lower(): char for char in characters}

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse "CHARACTER: dialogue" format
                if ":" not in line:
                    print(f"Warning: Line {line_num} missing colon, skipping: {line}")
                    continue

                character_name, dialogue = line.split(":", 1)
                character_name = character_name.strip()
                dialogue = dialogue.strip()

                # Find matching character
                character = character_map.get(character_name.lower())
                if not character:
                    # Create a basic character if not found
                    character = Character(name=character_name)
                    character_map[character_name.lower()] = character
                    print(
                        f"Warning: Character '{character_name}' not in config, created basic character"
                    )

                script_entries.append(
                    ScriptEntry(character=character, content=dialogue)
                )

            script = Script(entries=script_entries)

        return script

    def validate_script_format(self, script_str: str) -> List[str]:
        """Validate script format and return list of error messages"""
        errors = []
        for i, line in enumerate(script_str.split("\n"), 1):
            if line.strip() and ":" not in line:
                errors.append(f"Line {i}: Missing colon - '{line.strip()}'")
        return errors

    def parse_script_from_string(
        self, script_str: str, characters: List[Character]
    ) -> Script:
        """Parse script string into structured data"""
        # Validate first
        errors = self.validate_script_format(script_str)
        if errors:
            raise ValueError(f"Invalid script format: {', '.join(errors)}")

        # Parse valid entries
        script_entries = []
        for line in script_str.split("\n"):
            if ":" in line:
                character_name, content = line.split(":", 1)
                for character in characters:
                    if character.name.lower() == character_name.strip().lower():
                        # Match found, create ScriptEntry
                        script_entries.append(
                            ScriptEntry(character=character, content=content.strip())
                        )
                        break
                else:
                    # No match found, create a generic ScriptEntry
                    script_entries.append(
                        ScriptEntry(
                            character=Character(name=character_name.strip()),
                            content=content.strip(),
                        )
                    )

        if not script_entries:
            raise ValueError("No valid script entries found after parsing.")

        return Script(entries=script_entries)

    def load_from_json_file(self, file_path: Path) -> Script:
        """
        Load script entries from a JSON file.

        Format expected:
        [
            {
                "character": {"name": "Alice", "speaking_style": "formal", ...},
                "content": "Hello there!"
            },
            ...
        ]

        Args:
            file_path: Path to JSON file

        Returns:
            List of script entries, wrapped in a Script object
        """
        if not file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of script entries")

        script_entries = []
        for entry_data in data:
            # Load character
            char_data = entry_data["character"]
            character = Character(
                name=char_data["name"],
                speaking_style=char_data.get("speaking_style", ""),
                conversational_role=char_data.get("conversational_role", ""),
                image_path=Path(char_data.get("image_path", "")),
                tts_voice_clone=char_data.get("tts_voice_clone", ""),
                tts_voice_predefined=char_data.get("tts_voice_predefined", ""),
                tts_voice_profile=char_data.get("tts_voice_profile", ""),
                tts_voice_profile_overrides=char_data.get(
                    "tts_voice_profile_overrides", {}
                ),
            )

            script_entries.append(
                ScriptEntry(character=character, content=entry_data["content"])
            )

        script = Script(entries=script_entries)

        return script

    def load_auto_detect(
        self, file_path: Path, characters: List[Character] | None = None
    ) -> Script:
        """
        Auto-detect file format and load script entries.

        Args:
            file_path: Path to script file
            characters: Optional list of characters for matching

        Returns:
            List of script entries
        """
        if characters is None:
            characters = []

        suffix = file_path.suffix.lower()

        if suffix == ".json":
            return self.load_from_json_file(file_path)
        elif suffix in [".txt", ".script"]:
            return self.load_from_formatted_txt_file(file_path, characters)
        else:
            return self.load_from_formatted_txt_file(file_path, characters)

    def save_to_json_file(self, script: Script, file_path: Path) -> None:
        """
        Save script entries to a JSON file.

        Args:
            script_entries: List of script entries to save
            file_path: Path where to save the JSON file
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = []
        for entry in script.entries:
            entry_data = {
                "character": {
                    "name": entry.character.name,
                    "speaking_style": entry.character.speaking_style,
                    "conversational_role": entry.character.conversational_role,
                    "image_path": str(entry.character.image_path)
                    if entry.character.image_path
                    else "",
                    "tts_voice_clone": entry.character.tts_voice_clone,
                    "tts_voice_predefined": entry.character.tts_voice_predefined,
                    "tts_voice_profile": entry.character.tts_voice_profile,
                    "tts_voice_profile_overrides": entry.character.tts_voice_profile_overrides,
                },
                "content": entry.content,
            }
            data.append(entry_data)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    """Main function demonstrating script loading."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) != 2:
        print("Usage: python load_script_entries_use_case.py <script_file>")
        print("Supported formats: .txt (dialogue), .script (formatted), .json")
        sys.exit(1)

    script_file = Path(sys.argv[1])
    if not script_file.exists():
        print(f"Error: Script file not found: {script_file}")
        sys.exit(1)

    try:
        repository = ScriptRepository()
        script = repository.load_auto_detect(script_file)

        print(f"Loaded Script from: {script_file}")
        print("=" * 50)
        print(f"✓ Loaded {len(script.entries)} script entries")

        characters = list(set(entry.character.name for entry in script.entries))
        print(f"✓ Characters: {', '.join(characters)}")

        print("\nScript Preview:")
        print("-" * 30)

        for i, entry in enumerate(script.entries[:5], 1):  # Show first 5
            print(f"{i}. {entry.character.name}: {entry.content}")

        if len(script.entries) > 5:
            print(f"... and {len(script.entries) - 5} more entries")

    except Exception as e:
        print(f"Error loading script: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
