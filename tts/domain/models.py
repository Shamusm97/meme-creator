from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Union, Tuple
import requests


@dataclass
class ChatterboxVoiceProfile:
    """Represents a voice profile for Chatterbox TTS API."""

    temperature: float
    exaggeration: float
    cfg_weight: float
    seed: int
    speed_factor: float
    language: str


class TTSClient(ABC):
    """Abstract base class for TTS clients."""

    @abstractmethod
    def synthesize_to_stream(self, request: TTSRequest) -> requests.Response:
        """
        Synthesize text to speech and return streaming response.

        Args:
            request: TTS request configuration

        Returns:
            Streaming response object
        """
        pass

    @abstractmethod
    def save_stream_to_file(
        self, response: requests.Response, output_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Save streaming response to file.

        Args:
            response: Streaming response from synthesize_to_stream()
            output_path: Path where to save the audio file

        Returns:
            Dictionary with save info
        """
        pass

    @abstractmethod
    def synthesize_to_file(
        self, request: TTSRequest, output_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Synthesize text to speech and save to file.

        Args:
            request: TTS request configuration
            output_path: Path where to save the audio file

        Returns:
            Dictionary with synthesis info
        """
        pass

    @abstractmethod
    def synthesize_batch(
        self,
        texts: List[str],
        output_dir: Union[str, Path],
        base_config: TTSRequest,
        filename_prefix: str = "speech",
    ) -> List[Dict[str, Any]]:
        """
        Synthesize multiple texts to separate files.

        Args:
            texts: List of texts to synthesize
            output_dir: Directory to save audio files
            base_config: Base TTS configuration
            filename_prefix: Prefix for generated filenames

        Returns:
            List of synthesis results
        """
        pass

    @abstractmethod
    def get_reference_files(self) -> Dict[str, Any]:
        """
        Get list of available reference audio files.

        Returns:
            Dictionary with reference files info or error
        """
        pass

    @abstractmethod
    def get_predefined_voices(self) -> Dict[str, Any]:
        """
        Get list of available predefined voices.

        Returns:
            Dictionary with predefined voices info or error
        """
        pass

    @abstractmethod
    def upload_reference_audio(
        self, file_path: Union[str, Path], force_overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Upload reference audio file.

        Args:
            file_path: Path to the audio file to upload
            force_overwrite: If True, upload even if file already exists

        Returns:
            Dictionary with upload result
        """
        pass

    @abstractmethod
    def upload_predefined_voice(
        self, file_path: Union[str, Path], force_overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Upload predefined voice file.

        Args:
            file_path: Path to the voice file to upload
            force_overwrite: If True, upload even if file already exists

        Returns:
            Dictionary with upload result
        """
        pass

    @abstractmethod
    def batch_upload_reference_files(
        self, file_paths: List[Union[str, Path]], force_overwrite: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple reference audio files.

        Args:
            file_paths: List of paths to audio files
            force_overwrite: If True, upload even if files already exist

        Returns:
            List of upload results for each file
        """
        pass

    @abstractmethod
    def list_available_voices(self) -> Dict[str, Any]:
        """
        Get comprehensive list of both predefined voices and reference files.

        Returns:
            Dictionary with all available voices organized by type
        """
        pass


class TTSManager(ABC):
    """Abstract base class for TTS workflow managers."""

    def __init__(self, tts_client: TTSClient):
        self.tts_client = tts_client

    @abstractmethod
    def parse_script_lines(self, script: str) -> List[Tuple[str, str]]:
        """
        Parse script into (character, dialogue) pairs.

        Args:
            script: Script text

        Returns:
            List of (character, dialogue) tuples
        """
        pass

    @abstractmethod
    def generate_speech_files(
        self,
        script: str,
        output_dir: Union[str, Path],
        voice_mapping: Dict[str, str],
        base_config: TTSRequest,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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
        pass


# Example concrete implementations would inherit from these ABCs:
#
# class ChatterboxTTSRequest(TTSRequest):
#     def to_dict(self) -> Dict[str, Any]:
#         # Implementation here
#         pass
#
# class ChatterboxTTSClient(TTSClient):
#     # All abstract methods implemented
#     pass
#
# class TikTokTTSManager(TTSManager):
#     # All abstract methods implemented
#     pass
