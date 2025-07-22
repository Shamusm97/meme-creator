import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from config.domain.models import Character
from script.domain.models import ScriptEntry
from tts.domain.models import AudioFile, OutputFormat


class TTSFileService:
    """Service for handling TTS file operations like saving and filename generation."""

    def create_output_directory(self, output_dir: Path) -> None:
        """Create output directory if it doesn't exist."""
        output_dir.mkdir(parents=True, exist_ok=True)

    def generate_filename(
        self,
        character: Character,
        index: Optional[int] = None,
        output_format: OutputFormat = OutputFormat.WAV,
    ) -> str:
        """
        Generate filename for audio file.

        Args:
            character: Character for the audio
            index: Optional index for ordering
            output_format: Audio output format

        Returns:
            Generated filename string
        """
        character_name = character.name.lower().replace(" ", "_")

        if index is not None:
            return f"{index:03d}_{character_name}.{output_format.value}"
        else:
            return f"{character_name}.{output_format.value}"

    def save_audio_stream_to_file(
        self,
        response: requests.Response,
        output_path: Path,
        script_entry: ScriptEntry,
    ) -> AudioFile:
        """
        Save streaming audio response to file and create AudioFile.

        Args:
            response: Streaming response from TTS service
            output_path: Path where to save the audio file
            character: Character associated with the audio
            dialogue: Text content that was synthesized

        Returns:
            AudioFile domain object

        Raises:
            Exception: If saving fails
        """
        save_result = self._save_stream_to_file(response, output_path)

        if not save_result["success"]:
            raise Exception(f"Failed to save audio file: {save_result['error']}")

        # Estimate duration (rough calculation)
        words = len(script_entry.content.split())
        estimated_duration = (words / 150) * 60  # 150 words per minute

        return AudioFile(
            path=output_path,
            script_entry=script_entry,
            duration_seconds=estimated_duration,
            file_size_bytes=save_result["file_size_bytes"],
        )

    def _save_stream_to_file(
        self, response: requests.Response, output_path: Path
    ) -> Dict[str, Any]:
        """
        Save streaming response to file.

        Args:
            response: Streaming response from TTS service
            output_path: Path where to save the audio file

        Returns:
            Dictionary with save result information
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        total_bytes = 0

        try:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)

            return {
                "success": True,
                "output_path": str(output_path),
                "file_size_bytes": total_bytes,
                "save_time_seconds": time.time() - start_time,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "save_time_seconds": time.time() - start_time,
            }

    def rename_file_with_index(
        self,
        original_path: Path,
        index: int,
        character: Character,
        output_format: OutputFormat,
    ) -> Path:
        """
        Rename file to include index prefix.

        Args:
            original_path: Original file path
            index: Index to include in filename
            character: Character for generating new name
            output_format: Audio output format

        Returns:
            New path after rename
        """
        filename = self.generate_filename(character, index, output_format)
        new_path = original_path.parent / filename
        original_path.rename(new_path)
        return new_path

    def estimate_duration_from_text(
        self, text: str, words_per_minute: int = 150
    ) -> float:
        """
        Estimate audio duration from text length.

        Args:
            text: Text to estimate duration for
            words_per_minute: Speaking rate (default 150 WPM)

        Returns:
            Estimated duration in seconds
        """
        words = len(text.split())
        return (words / words_per_minute) * 60

    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information
        """
        if not file_path.exists():
            return {"exists": False, "error": f"File not found: {file_path}"}

        try:
            stat = file_path.stat()
            return {
                "exists": True,
                "size_bytes": stat.st_size,
                "modified_time": stat.st_mtime,
                "name": file_path.name,
                "suffix": file_path.suffix,
                "parent": str(file_path.parent),
            }
        except Exception as e:
            return {"exists": True, "error": f"Could not get file info: {e}"}

