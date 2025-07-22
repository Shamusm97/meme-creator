"""Repository for AudioScript persistence and file operations."""

import json
import wave
from pathlib import Path
from typing import List, Optional
import subprocess
import os

from config.domain.models import Character
from tts.domain.models import AudioScript, AudioFile


class AudioScriptRepository:
    """Repository for saving and loading AudioScript data with metadata."""

    def __init__(self):
        self.supported_audio_extensions = [".wav", ".mp3", ".opus", ".m4a", ".flac"]

    def save_audio_script_metadata(
        self, audio_script: AudioScript, output_path: Path
    ) -> None:
        """
        Save audio script with timing metadata to JSON file.

        Args:
            audio_script: AudioScript containing audio files with timing
            output_path: Path where to save the JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "total_duration_seconds": audio_script.total_duration_seconds,
            "audio_files": [],
        }

        current_start_time = 0.0
        for audio_file in audio_script.audio_files:
            file_data = {
                "character": {
                    "name": audio_file.character.name,
                    "speaking_style": audio_file.character.speaking_style,
                    "conversational_role": audio_file.character.conversational_role,
                    "image_path": str(audio_file.character.image_path)
                    if audio_file.character.image_path
                    else "",
                    "tts_voice_clone": audio_file.character.tts_voice_clone,
                    "tts_voice_predefined": audio_file.character.tts_voice_predefined,
                    "tts_voice_profile": audio_file.character.tts_voice_profile,
                    "tts_voice_profile_overrides": audio_file.character.tts_voice_profile_overrides,
                },
                "dialogue": audio_file.dialogue,
                "audio_metadata": {
                    "filename": audio_file.path.name,
                    "full_path": str(audio_file.path),
                    "duration_seconds": audio_file.duration_seconds or 0.0,
                    "file_size_bytes": audio_file.file_size_bytes or 0,
                    "start_time": current_start_time,
                    "end_time": current_start_time
                    + (audio_file.duration_seconds or 0.0),
                },
            }
            data["audio_files"].append(file_data)
            current_start_time += audio_file.duration_seconds or 0.0

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_audio_script_as_srt(
        self, audio_script: AudioScript, output_path: Path
    ) -> None:
        """
        Save audio script as SRT subtitle file.

        Args:
            audio_script: AudioScript containing audio files with timing
            output_path: Path where to save the SRT file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        srt_content = []
        current_start_time = 0.0
        subtitle_index = 1

        for audio_file in audio_script.audio_files:
            if audio_file.script_entry:  # Only process files with script entries
                start_time = current_start_time
                end_time = start_time + (audio_file.duration_seconds or 0.0)
                
                # Format timestamps as SRT format (HH:MM:SS,mmm)
                start_timestamp = self._format_srt_timestamp(start_time)
                end_timestamp = self._format_srt_timestamp(end_time)
                
                # Create SRT subtitle entry
                subtitle = f"{subtitle_index}\n{start_timestamp} --> {end_timestamp}\n{audio_file.script_entry.content}\n"
                srt_content.append(subtitle)
                
                subtitle_index += 1
                current_start_time = end_time

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        Format seconds as SRT timestamp (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def load_audio_script_with_fallback(self, audio_dir: Path) -> Optional[AudioScript]:
        """
        Load AudioScript from directory with fallback strategy:
        1. Try JSON metadata file
        2. Try SRT subtitle file 
        3. Return None if neither found
        
        Args:
            audio_dir: Directory containing audio files and metadata
            
        Returns:
            AudioScript if metadata found, None otherwise
        """
        if not audio_dir.exists():
            return None
            
        # Try JSON first (preserves full character data)
        json_file = audio_dir / "audio_script_metadata.json"
        if json_file.exists():
            try:
                return self.load_audio_script_from_json_metadata(json_file)
            except Exception as e:
                print(f"Warning: Failed to load JSON metadata: {e}")
        
        # Try SRT fallback (basic subtitle data only)
        srt_file = audio_dir / "subtitles.srt"
        if srt_file.exists():
            try:
                return self.load_audio_script_from_srt(srt_file, audio_dir)
            except Exception as e:
                print(f"Warning: Failed to load SRT metadata: {e}")
                
        return None

    def load_audio_script_from_json_metadata(self, json_path: Path) -> AudioScript:
        """
        Load AudioScript from JSON metadata file.
        
        Args:
            json_path: Path to JSON metadata file
            
        Returns:
            AudioScript reconstructed from metadata
        """
        metadata = self.load_audio_script_metadata(json_path)
        audio_script = AudioScript()
        
        for file_data in metadata.get("audio_files", []):
            char_data = file_data["character"]
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
            
            audio_metadata = file_data["audio_metadata"]
            audio_file = AudioFile(
                path=Path(audio_metadata["full_path"]),
                script_entry=None,  # Could recreate ScriptEntry here if needed
                duration_seconds=audio_metadata.get("duration_seconds"),
                file_size_bytes=audio_metadata.get("file_size_bytes"),
            )
            
            audio_script.add_audio_file(audio_file)
            
        return audio_script

    def load_audio_script_from_srt(self, srt_path: Path, audio_dir: Path) -> AudioScript:
        """
        Load AudioScript from SRT subtitle file (limited metadata).
        
        Args:
            srt_path: Path to SRT file
            audio_dir: Directory containing audio files
            
        Returns:
            AudioScript with basic timing from SRT
        """
        audio_script = AudioScript()
        
        with open(srt_path, "r", encoding="utf-8") as f:
            srt_content = f.read()
            
        # Parse SRT format
        subtitle_blocks = srt_content.strip().split("\n\n")
        
        for block in subtitle_blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                # subtitle_number = lines[0]
                timestamp_line = lines[1]
                subtitle_text = "\n".join(lines[2:])
                
                # Parse timestamps (basic implementation)
                if " --> " in timestamp_line:
                    start_time, end_time = timestamp_line.split(" --> ")
                    duration = self._parse_srt_timestamp(end_time) - self._parse_srt_timestamp(start_time)
                    
                    # Create basic character and audio file
                    character = Character(name="Unknown")
                    
                    # Try to find corresponding audio file (basic matching)
                    audio_files = self.find_audio_files(audio_dir)
                    audio_path = audio_files[0] if audio_files else audio_dir / "unknown.wav"
                    
                    audio_file = AudioFile(
                        path=audio_path,
                        script_entry=None,
                        duration_seconds=duration,
                        file_size_bytes=None,
                    )
                    
                    audio_script.add_audio_file(audio_file)
                    
        return audio_script

    def _parse_srt_timestamp(self, timestamp: str) -> float:
        """Parse SRT timestamp (HH:MM:SS,mmm) to seconds."""
        try:
            time_part, ms_part = timestamp.strip().split(",")
            hours, minutes, seconds = map(int, time_part.split(":"))
            milliseconds = int(ms_part)
            
            return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        except Exception:
            return 0.0

    def load_audio_script_metadata(self, json_path: Path) -> dict:
        """
        Load audio script metadata from JSON file.

        Args:
            json_path: Path to the JSON file

        Returns:
            Dictionary containing the audio script metadata
        """
        if not json_path.exists():
            raise FileNotFoundError(
                f"Audio script metadata file not found: {json_path}"
            )

        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_audio_script_from_directory(
        self, audio_dir: Path, characters: Optional[List[Character]] = None
    ) -> AudioScript:
        """
        Load AudioScript from directory containing audio files.

        Args:
            audio_dir: Directory containing audio files
            characters: Optional list of characters for mapping

        Returns:
            AudioScript with loaded audio files
        """
        if not audio_dir.exists():
            raise FileNotFoundError(f"Audio directory not found: {audio_dir}")

        characters = characters or []
        character_map = {char.name.lower(): char for char in characters}

        # Try to load character mapping and content from script_entries.json
        script_entries_file = audio_dir / "script_entries.json"
        script_content_map = {}
        if script_entries_file.exists():
            character_map.update(self._load_character_mapping(script_entries_file))
            script_content_map = self._load_script_content_mapping(script_entries_file)

        audio_files = self.find_audio_files(audio_dir)
        audio_script = AudioScript()

        for audio_file_path in audio_files:
            try:
                # Extract character name from filename (assumes format: "001_CharacterName.wav")
                filename_parts = audio_file_path.stem.split("_", 1)
                if len(filename_parts) >= 2:
                    character_name = filename_parts[1]
                else:
                    character_name = audio_file_path.stem

                # Find matching character
                character = character_map.get(character_name.lower())
                if not character:
                    character = Character(name=character_name)
                    print(f"Warning: Character '{character_name}' not found, created basic character")

                # Get audio duration
                duration = self._get_audio_duration(audio_file_path)
                
                # Get file size
                file_size = audio_file_path.stat().st_size if audio_file_path.exists() else None

                # Try to get actual dialogue content from script entries
                dialogue = self._get_dialogue_for_file(audio_file_path, script_content_map)
                if not dialogue:
                    dialogue = f"Audio from {audio_file_path.name}"

                # Create AudioFile
                audio_file = AudioFile(
                    path=audio_file_path,
                    character=character,
                    dialogue=dialogue,
                    duration_seconds=duration,
                    file_size_bytes=file_size,
                )

                audio_script.add_audio_file(audio_file)

            except Exception as e:
                print(f"Warning: Could not load audio file {audio_file_path}: {e}")
                continue

        return audio_script

    def find_audio_files(self, directory: Path) -> List[Path]:
        """
        Find all audio files in a directory.

        Args:
            directory: Directory to search

        Returns:
            List of audio file paths, sorted by name
        """
        audio_files = []
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_audio_extensions:
                audio_files.append(file_path)
        
        return sorted(audio_files)

    def save_character_mapping(self, characters: List[Character], output_path: Path) -> None:
        """
        Save character mapping to JSON file.

        Args:
            characters: List of characters to save
            output_path: Path where to save the mapping
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = []
        for character in characters:
            character_data = {
                "character": {
                    "name": character.name,
                    "speaking_style": character.speaking_style,
                    "conversational_role": character.conversational_role,
                    "image_path": str(character.image_path) if character.image_path else "",
                    "tts_voice_clone": character.tts_voice_clone,
                    "tts_voice_predefined": character.tts_voice_predefined,
                    "tts_voice_profile": character.tts_voice_profile,
                    "tts_voice_profile_overrides": character.tts_voice_profile_overrides,
                }
            }
            data.append(character_data)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_character_mapping(self, json_path: Path) -> dict:
        """Load character mapping from JSON file."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            character_map = {}
            for entry in data:
                char_data = entry["character"]
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
                character_map[character.name.lower()] = character
                
            return character_map
            
        except Exception as e:
            print(f"Warning: Could not load character mapping: {e}")
            return {}

    def _load_script_content_mapping(self, json_path: Path) -> dict:
        """Load script content mapping from JSON file (indexed by entry order)."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            content_map = {}
            for index, entry in enumerate(data):
                # Map by index for ordered matching with audio files
                content_map[index] = {
                    'content': entry.get('content', ''),
                    'character_name': entry.get('character', {}).get('name', '')
                }
                
            return content_map
            
        except Exception as e:
            print(f"Warning: Could not load script content mapping: {e}")
            return {}

    def _get_dialogue_for_file(self, audio_file_path: Path, script_content_map: dict) -> str:
        """Get dialogue content for audio file based on filename index."""
        try:
            # Extract index from filename (assumes format: "001_CharacterName.wav")
            filename_parts = audio_file_path.stem.split("_", 1)
            if len(filename_parts) >= 1 and filename_parts[0].isdigit():
                file_index = int(filename_parts[0])
                if file_index in script_content_map:
                    return script_content_map[file_index]['content']
            return ""
        except Exception as e:
            print(f"Warning: Could not extract dialogue for {audio_file_path}: {e}")
            return ""

    def _get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Get audio file duration using multiple methods."""
        try:
            # Try librosa first (most accurate but requires dependency)
            try:
                import librosa
                duration = librosa.get_duration(path=str(audio_path))
                return float(duration)
            except ImportError:
                pass

            # Try wave module for WAV files
            if audio_path.suffix.lower() == '.wav':
                try:
                    with wave.open(str(audio_path), 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        duration = frames / float(rate)
                        return duration
                except Exception:
                    pass

            # Try ffprobe as fallback
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', str(audio_path)
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip():
                    return float(result.stdout.strip())
            except (subprocess.SubprocessError, subprocess.TimeoutExpired, ValueError):
                pass

            # Estimate from file size as last resort
            file_size = audio_path.stat().st_size
            estimated_duration = file_size / (44100 * 2 * 2)  # Assume 44.1kHz, 16-bit, stereo
            return max(0.1, estimated_duration)  # Minimum 0.1 seconds
            
        except Exception as e:
            print(f"Warning: Could not determine duration for {audio_path}: {e}")
            return None