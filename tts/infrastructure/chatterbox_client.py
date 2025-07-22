from dataclasses import dataclass, asdict, field
from typing import Optional, Union, List
from enum import Enum
from pathlib import Path
import time
import requests

from tts.domain.models import (
    VoiceProfile,
    TTSRequest,
    TTSService,
    AudioFile,
    AudioScript,
)
from tts.infrastructure.tts_file_service import TTSFileService


@dataclass
class ChatterboxTTSConfig:
    """Configuration specific to Chatterbox TTS provider"""

    base_url: str
    endpoint: str = field(default="/tts")
    timeout: int = field(default=120)

    def __post_init__(self):
        if not self.base_url.strip():
            raise ValueError("Base URL cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")


class CHATTERBOX_VOICE_PROFILES(Enum):
    """
    Enum for predefined voice profiles used in Chatterbox TTS API.
    """

    STANDARD_NARRATION = VoiceProfile(
        temperature=0.8,
        exaggeration=0.4,
        cfg_weight=0.5,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    EXPRESSIVE_MONOLOGUE = VoiceProfile(
        temperature=0.75,
        exaggeration=1.1,
        cfg_weight=0.6,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    TECHNICAL_EXPLANATION = VoiceProfile(
        temperature=0.85,
        exaggeration=0.4,
        cfg_weight=0.5,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    UPBEAT_ADVERTISEMENT = VoiceProfile(
        temperature=0.8,
        exaggeration=1.3,
        cfg_weight=0.45,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    THOUGHTFUL_REFLECTION = VoiceProfile(
        temperature=0.7,
        exaggeration=0.4,
        cfg_weight=0.6,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    SIMPLE_PUNCTUATION_TEST = VoiceProfile(
        temperature=0.8,
        exaggeration=0.5,
        cfg_weight=0.5,
        seed=0,
        speed_factor=1.0,
        language="en",
    )
    LONG_STORY_EXCERPT = VoiceProfile(
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
    Infrastructure model for Chatterbox TTS API requests.
    """

    text: str
    voice_mode: str
    predefined_voice_id: Optional[str] = None
    reference_audio_filename: Optional[str] = None
    output_format: str = "wav"
    split_text: bool = True
    chunk_size: int = 120
    voice_profile: Optional[VoiceProfile] = None

    @classmethod
    def from_domain_request(cls, domain_request: TTSRequest) -> "ChatterboxTTSRequest":
        """Convert domain TTSRequest to infrastructure request."""
        return cls(
            text=domain_request.text,
            voice_mode=domain_request.voice_mode.value,
            predefined_voice_id=domain_request.predefined_voice_id,
            reference_audio_filename=domain_request.reference_audio_filename,
            output_format=domain_request.output_format.value,
            split_text=domain_request.split_text,
            chunk_size=domain_request.chunk_size,
            voice_profile=domain_request.voice_profile,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API request."""
        result = {
            "text": self.text,
            "voice_mode": self.voice_mode,
            "output_format": self.output_format,
            "split_text": self.split_text,
            "chunk_size": self.chunk_size,
        }

        if self.predefined_voice_id is not None:
            result["predefined_voice_id"] = self.predefined_voice_id
        if self.reference_audio_filename is not None:
            result["reference_audio_filename"] = self.reference_audio_filename

        if self.voice_profile is not None:
            profile_dict = asdict(self.voice_profile)
            for key, value in profile_dict.items():
                if value is not None:
                    result[key] = value

        return result


class ChatterboxTTSClient(TTSService):
    """
    Chatterbox implementation of TTSService.
    """

    def __init__(self, config: ChatterboxTTSConfig, tts_file_service: TTSFileService = None):
        """
        Initialize Chatterbox TTS Client.

        Args:
            config: Chatterbox TTS configuration
            tts_file_service: Service for handling file operations
        """
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.tts_endpoint = f"{self.base_url}{config.endpoint}"
        self.timeout = config.timeout
        self.session = requests.Session()
        self.file_service = tts_file_service or TTSFileService()

    def synthesize(self, request: TTSRequest, output_dir: Path) -> AudioFile:
        """Synthesize speech for a single request."""
        # Ensure output directory exists
        self.file_service.create_output_directory(output_dir)
        
        chatterbox_request = ChatterboxTTSRequest.from_domain_request(request)
        response = self._synthesize_to_stream(chatterbox_request)

        # Generate filename using file service
        filename = self.file_service.generate_filename(
            request.character, output_format=request.output_format
        )
        output_path = output_dir / filename

        # Save using file service
        return self.file_service.save_audio_stream_to_file(
            response, output_path, request.character, request.text
        )

    def synthesize_script(
        self, requests: List[TTSRequest], output_dir: Path
    ) -> AudioScript:
        """Synthesize speech for multiple requests."""
        self.file_service.create_output_directory(output_dir)
        speech_script = AudioScript()

        for i, request in enumerate(requests):
            # Synthesize to temporary location
            audio_file = self.synthesize(request, output_dir)

            # Rename with index prefix using file service
            indexed_path = self.file_service.rename_file_with_index(
                audio_file.path, i, request.character, request.output_format
            )

            # Update the audio file path
            audio_file = AudioFile(
                path=indexed_path,
                character=audio_file.character,
                dialogue=audio_file.dialogue,
                duration_seconds=audio_file.duration_seconds,
                file_size_bytes=audio_file.file_size_bytes,
            )

            speech_script.add_audio_file(audio_file)

        return speech_script

    def _synthesize_to_stream(self, request: ChatterboxTTSRequest) -> requests.Response:
        """
        Synthesize text to speech and return streaming response.

        Args:
            request: TTS request configuration

        Returns:
            Streaming response object
        """
        response = None
        try:
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
        except requests.exceptions.HTTPError as e:
            if response is None:
                raise Exception(
                    f"Failed to receive response from TTS server at {self.tts_endpoint}: {str(e)}"
                )
            if response.status_code == 404:
                try:
                    error_detail = response.json().get("detail", "Resource not found")
                    if "not found" in error_detail.lower():
                        if (
                            request.voice_mode == "clone"
                            and request.reference_audio_filename
                        ):
                            raise Exception(
                                f"Voice clone file '{request.reference_audio_filename}' not found on TTS server. "
                                f"Please upload the file or use a predefined voice instead."
                            )
                        elif (
                            request.voice_mode == "predefined"
                            and request.predefined_voice_id
                        ):
                            raise Exception(
                                f"Predefined voice '{request.predefined_voice_id}' not found on TTS server. "
                                f"Check available voices with get_predefined_voices()."
                            )
                        else:
                            raise Exception(f"TTS resource not found: {error_detail}")
                    else:
                        raise Exception(f"TTS server error (404): {error_detail}")
                except (ValueError, KeyError):
                    raise Exception(f"TTS server returned 404: {response.text}")
            else:
                raise Exception(
                    f"TTS server error ({response.status_code}): {response.text}"
                )
        except requests.exceptions.RequestException as e:
            raise Exception(
                f"Failed to connect to TTS server at {self.tts_endpoint}: {str(e)}"
            )


    def _synthesize_to_file(
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
            response = self._synthesize_to_stream(request)

            # Save stream to file
            save_result = self._save_stream_to_file(response, output_path)

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
            result = self._synthesize_to_file(request, output_path)
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
