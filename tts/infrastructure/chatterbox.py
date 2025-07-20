from dataclasses import dataclass, asdict
from typing import Optional, Union
from enum import Enum
from pathlib import Path
import time
import json
import requests
from tts.domain.models import ChatterboxVoiceProfile


class CHATTERBOX_VOICE_PROFILES(Enum):
    """
    Enum for predefined voice profiles used in Chatterbox TTS API.
    """

    STANDARD_NARRATION = ChatterboxVoiceProfile(
        temperature=0.8,
        exaggeration=0.4,
        cfg_weight=0.5,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    EXPRESSIVE_MONOLOGUE = ChatterboxVoiceProfile(
        temperature=0.75,
        exaggeration=1.1,
        cfg_weight=0.6,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    TECHNICAL_EXPLANATION = ChatterboxVoiceProfile(
        temperature=0.85,
        exaggeration=0.4,
        cfg_weight=0.5,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    UPBEAT_ADVERTISEMENT = ChatterboxVoiceProfile(
        temperature=0.8,
        exaggeration=1.3,
        cfg_weight=0.45,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    THOUGHTFUL_REFLECTION = ChatterboxVoiceProfile(
        temperature=0.7,
        exaggeration=0.4,
        cfg_weight=0.6,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    SIMPLE_PUNCTUATION_TEST = ChatterboxVoiceProfile(
        temperature=0.8,
        exaggeration=0.5,
        cfg_weight=0.5,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    LONG_STORY_EXCERPT = ChatterboxVoiceProfile(
        temperature=0.78,
        exaggeration=1.1,
        cfg_weight=0.55,
        seed=0,
        speed_factor=1.0,
        language="en",
    )


@dataclass
class ChatterboxTTSRequest:
    """
    Request configuration for Chatterbox TTS API.
    """

    text: str
    voice_mode: str = "predefined"  # "predefined" or "clone"
    predefined_voice_id: Optional[str] = None
    reference_audio_filename: Optional[str] = None
    output_format: str = "wav"  # "wav" or "opus"
    split_text: bool = True
    chunk_size: int = 120
    voice_profile: Optional[ChatterboxVoiceProfile] = None

    def __post_init__(self):
        """Validate the request configuration."""
        if self.voice_mode not in ["predefined", "clone"]:
            raise ValueError("voice_mode must be 'predefined' or 'clone'")

        if self.voice_mode == "predefined" and not self.predefined_voice_id:
            raise ValueError(
                "predefined_voice_id is required when voice_mode is 'predefined'"
            )

        if self.voice_mode == "clone" and not self.reference_audio_filename:
            raise ValueError(
                "reference_audio_filename is required when voice_mode is 'clone'"
            )

        if self.output_format not in ["wav", "opus"]:
            raise ValueError("output_format must be 'wav' or 'opus'")

    def to_dict(self) -> dict:
        """Convert to dictionary, flattening voice_profile and excluding None values."""
        # Start with basic fields
        result = {
            "text": self.text,
            "voice_mode": self.voice_mode,
            "output_format": self.output_format,
            "split_text": self.split_text,
            "chunk_size": self.chunk_size,
        }

        # Add optional basic fields
        if self.predefined_voice_id is not None:
            result["predefined_voice_id"] = self.predefined_voice_id
        if self.reference_audio_filename is not None:
            result["reference_audio_filename"] = self.reference_audio_filename

        # Flatten voice_profile fields if present
        if self.voice_profile is not None:
            profile_dict = asdict(self.voice_profile)
            # Add non-None voice profile fields directly to result
            for key, value in profile_dict.items():
                if value is not None:
                    result[key] = value

        return result


class ChatterboxTTSClient:
    """
    Client for Chatterbox TTS API with streaming support.
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize Chatterbox TTS Client.

        Args:
            base_url: Base URL of the Chatterbox TTS API (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.tts_endpoint = f"{self.base_url}/tts"
        self.timeout = timeout
        self.session = requests.Session()

    def synthesize_to_stream(self, request: ChatterboxTTSRequest) -> requests.Response:
        """
        Synthesize text to speech and return streaming response.

        Args:
            request: TTS request configuration

        Returns:
            Streaming response object
        """
        response = self.session.post(
            self.tts_endpoint,
            json=request.to_dict(),
            headers={
                "Content-Type": "application/json",
                "Accept": f"audio/{request.output_format}",
            },
            stream=True,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def save_stream_to_file(
        self, response: requests.Response, output_path: Union[str, Path]
    ) -> dict:
        """
        Save streaming response to file.

        Args:
            response: Streaming response from synthesize_to_stream()
            output_path: Path where to save the audio file

        Returns:
            Dictionary with save info
        """
        output_path = Path(output_path)
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

    def synthesize_to_file(
        self, request: ChatterboxTTSRequest, output_path: Union[str, Path]
    ) -> dict:
        """
        Synthesize text to speech and save to file using streaming.

        Args:
            request: TTS request configuration
            output_path: Path where to save the audio file

        Returns:
            Dictionary with synthesis info (duration, file_size, etc.)
        """
        start_time = time.time()

        try:
            # Get streaming response
            response = self.synthesize_to_stream(request)

            # Save stream to file
            save_result = self.save_stream_to_file(response, output_path)

            synthesis_time = time.time() - start_time

            if save_result["success"]:
                return {
                    "success": True,
                    "output_path": save_result["output_path"],
                    "file_size_bytes": save_result["file_size_bytes"],
                    "synthesis_time_seconds": synthesis_time,
                    "text_length": len(request.text),
                    "output_format": request.output_format,
                    "voice_mode": request.voice_mode,
                    "voice_id": request.predefined_voice_id
                    or request.reference_audio_filename,
                }
            else:
                return {
                    "success": False,
                    "error": save_result["error"],
                    "synthesis_time_seconds": synthesis_time,
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "synthesis_time_seconds": time.time() - start_time,
            }

    def synthesize_batch(
        self,
        texts: list[str],
        output_dir: Union[str, Path],
        base_config: ChatterboxTTSRequest,
        filename_prefix: str = "speech",
    ) -> list[dict]:
        """
        Synthesize multiple texts to separate files.

        Args:
            texts: List of texts to synthesize
            output_dir: Directory to save audio files
            base_config: Base TTS configuration (text will be overridden)
            filename_prefix: Prefix for generated filenames

        Returns:
            List of synthesis results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []

        for i, text in enumerate(texts):
            # Create new request with current text
            request = ChatterboxTTSRequest(
                text=text,
                voice_mode=base_config.voice_mode,
                predefined_voice_id=base_config.predefined_voice_id,
                reference_audio_filename=base_config.reference_audio_filename,
                output_format=base_config.output_format,
                split_text=base_config.split_text,
                chunk_size=base_config.chunk_size,
                voice_profile=base_config.voice_profile,
            )

            # Generate filename
            filename = f"{filename_prefix}_{i:03d}.{request.output_format}"
            output_path = output_dir / filename

            # Synthesize using stream-based method
            result = self.synthesize_to_file(request, output_path)
            result["index"] = i
            result["text"] = text
            results.append(result)

            print(f"Synthesized {i + 1}/{len(texts)}: {filename}")

        return results

    def get_reference_files(self) -> dict:
        """
        Get list of available reference audio files.

        Returns:
            Dictionary with reference files info or error
        """
        try:
            response = self.session.get(
                f"{self.base_url}/get_reference_files", timeout=self.timeout
            )
            response.raise_for_status()
            return {"success": True, "files": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e), "files": []}

    def get_predefined_voices(self) -> dict:
        """
        Get list of available predefined voices.

        Returns:
            Dictionary with predefined voices info or error
        """
        try:
            response = self.session.get(
                f"{self.base_url}/get_predefined_voices", timeout=self.timeout
            )
            response.raise_for_status()
            return {"success": True, "voices": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e), "voices": []}

    def upload_reference_audio(
        self, file_path: Union[str, Path], force_overwrite: bool = False
    ) -> dict:
        """
        Upload reference audio file, checking for existing files first.

        Args:
            file_path: Path to the audio file to upload
            force_overwrite: If True, upload even if file already exists

        Returns:
            Dictionary with upload result
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "uploaded": False,
            }

        filename = file_path.name

        # Check if file already exists
        if not force_overwrite:
            existing_files = self.get_reference_files()
            if existing_files["success"]:
                existing_names = [
                    f.get("name", f) if isinstance(f, dict) else f
                    for f in existing_files["files"]
                ]
                if filename in existing_names:
                    return {
                        "success": False,
                        "error": f"File '{filename}' already exists. Use force_overwrite=True to replace it.",
                        "uploaded": False,
                        "existing_file": True,
                    }

        # Upload the file
        try:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "audio/*")}
                response = self.session.post(
                    f"{self.base_url}/upload_reference",
                    files=files,
                    timeout=self.timeout,
                )
                response.raise_for_status()

            return {
                "success": True,
                "message": f"Successfully uploaded '{filename}'",
                "uploaded": True,
                "filename": filename,
                "overwritten": force_overwrite,
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Upload failed: {str(e)}",
                "uploaded": False,
            }

    def upload_predefined_voice(
        self, file_path: Union[str, Path], force_overwrite: bool = False
    ) -> dict:
        """
        Upload predefined voice file, checking for existing files first.

        Args:
            file_path: Path to the voice file to upload
            force_overwrite: If True, upload even if file already exists

        Returns:
            Dictionary with upload result
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "uploaded": False,
            }

        filename = file_path.name

        # Check if file already exists
        if not force_overwrite:
            existing_voices = self.get_predefined_voices()
            if existing_voices["success"]:
                existing_names = [
                    v.get("name", v) if isinstance(v, dict) else v
                    for v in existing_voices["voices"]
                ]
                if filename in existing_names:
                    return {
                        "success": False,
                        "error": f"Voice '{filename}' already exists. Use force_overwrite=True to replace it.",
                        "uploaded": False,
                        "existing_file": True,
                    }

        # Upload the file
        try:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "audio/*")}
                response = self.session.post(
                    f"{self.base_url}/upload_predefined_voice",
                    files=files,
                    timeout=self.timeout,
                )
                response.raise_for_status()

            return {
                "success": True,
                "message": f"Successfully uploaded voice '{filename}'",
                "uploaded": True,
                "filename": filename,
                "overwritten": force_overwrite,
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Voice upload failed: {str(e)}",
                "uploaded": False,
            }

    def batch_upload_reference_files(
        self, file_paths: list[Union[str, Path]], force_overwrite: bool = False
    ) -> list[dict]:
        """
        Upload multiple reference audio files.

        Args:
            file_paths: List of paths to audio files
            force_overwrite: If True, upload even if files already exist

        Returns:
            List of upload results for each file
        """
        results = []

        for file_path in file_paths:
            result = self.upload_reference_audio(file_path, force_overwrite)
            result["file_path"] = str(file_path)
            results.append(result)

            # Print progress
            status = "✓" if result["success"] else "✗"
            filename = Path(file_path).name
            print(
                f"{status} {filename}: {result.get('message', result.get('error', 'Unknown'))}"
            )

        return results

    def list_available_voices(self) -> dict:
        """
        Get comprehensive list of both predefined voices and reference files.

        Returns:
            Dictionary with all available voices organized by type
        """
        predefined = self.get_predefined_voices()
        reference = self.get_reference_files()

        return {
            "success": predefined["success"] and reference["success"],
            "predefined_voices": predefined["voices"] if predefined["success"] else [],
            "reference_files": reference["files"] if reference["success"] else [],
            "total_voices": (
                len(predefined.get("voices", [])) + len(reference.get("files", []))
            ),
            "errors": {
                "predefined": None if predefined["success"] else predefined["error"],
                "reference": None if reference["success"] else reference["error"],
            },
        }


# Utility functions for TikTok workflow integration
class TikTokTTSManager:
    """
    Manager class specifically for TikTok video workflow.
    """

    def __init__(self, tts_client: ChatterboxTTSClient):
        self.tts_client = tts_client

    def parse_script_lines(self, script: str) -> list[tuple[str, str]]:
        """
        Parse script into (character, dialogue) pairs.

        Args:
            script: Script text with format "CHARACTER: dialogue"

        Returns:
            List of (character, dialogue) tuples
        """
        lines = []
        for line in script.strip().split("\n"):
            line = line.strip()
            if ":" in line and line:
                character, dialogue = line.split(":", 1)
                lines.append((character.strip(), dialogue.strip()))
        return lines

    def generate_speech_files(
        self,
        script: str,
        output_dir: Union[str, Path],
        voice_mapping: dict[str, str],
        base_config: ChatterboxTTSRequest,
    ) -> tuple[list[dict], list[dict]]:
        """
        Generate speech files for entire script with character voice mapping.

        Args:
            script: Script text
            output_dir: Directory to save audio files
            voice_mapping: Dict mapping character names to voice IDs
            base_config: Base TTS configuration

        Returns:
            Tuple of (synthesis_results, timing_data)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Parse script
        script_lines = self.parse_script_lines(script)

        synthesis_results = []
        timing_data = []
        current_time = 0

        for i, (character, dialogue) in enumerate(script_lines):
            # Get voice for character (fallback to first voice if not mapped)
            voice_id = voice_mapping.get(character, list(voice_mapping.values())[0])

            # Create request for this line
            request = ChatterboxTTSRequest(
                text=dialogue,
                voice_mode=base_config.voice_mode,
                predefined_voice_id=voice_id
                if base_config.voice_mode == "predefined"
                else None,
                reference_audio_filename=voice_id
                if base_config.voice_mode == "clone"
                else None,
                output_format=base_config.output_format,
                split_text=base_config.split_text,
                chunk_size=base_config.chunk_size,
                voice_profile=base_config.voice_profile,
            )

            # Generate filename
            filename = (
                f"{i:03d}_{character.lower().replace(' ', '_')}.{request.output_format}"
            )
            output_path = output_dir / filename

            # Synthesize using stream-based method
            result = self.tts_client.synthesize_to_file(request, output_path)
            result.update(
                {
                    "index": i,
                    "character": character,
                    "dialogue": dialogue,
                    "filename": filename,
                }
            )
            synthesis_results.append(result)

            # Estimate duration (rough estimate: 150 words per minute)
            words = len(dialogue.split())
            estimated_duration = (words / 150) * 60  # seconds

            timing_data.append(
                {
                    "character": character,
                    "dialogue": dialogue,
                    "filename": filename,
                    "start_time": current_time,
                    "duration": estimated_duration,
                    "index": i,
                }
            )

            current_time += estimated_duration

            print(f"Generated {i + 1}/{len(script_lines)}: {character} - {filename}")

        # Save timing data
        timing_file = output_dir / "timing_data.json"
        with open(timing_file, "w") as f:
            json.dump(timing_data, f, indent=2)

        # Save master order file
        master_file = output_dir / "master.txt"
        with open(master_file, "w") as f:
            for item in timing_data:
                f.write(f"{item['filename']}\n")

        return synthesis_results, timing_data


if __name__ == "__main__":
    # Example usage
    client = ChatterboxTTSClient(base_url="http://localhost:8004")

    # Define a base TTS request configuration
    base_config = ChatterboxTTSRequest(
        text="My name is peter and I like fags, also known as cigarettes",
        voice_mode="clone",
        reference_audio_filename="Petersmall.mp3",
        output_format="wav",
        split_text=True,
        chunk_size=120,
        voice_profile=CHATTERBOX_VOICE_PROFILES.EXPRESSIVE_MONOLOGUE.value,
    )

    output_dir = Path("")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        response = client.synthesize_to_file(
            request=base_config, output_path="output.wav"
        )
        print("Synthesis completed successfully.")
        print(f"response: {response}")
        print(f"Output saved to: {response['output_path']}")
    except Exception as e:
        print(f"Error during synthesis: {e}")

