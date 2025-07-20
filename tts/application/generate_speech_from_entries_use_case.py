from pathlib import Path
from typing import List

from config.domain.models import TTSConfig
from script.domain.models import ScriptEntry
from tts.domain.models import (
    TTSRequest,
    AudioScript,
    VoiceMode,
    OutputFormat,
)
from tts.application.tts_service_factory import TTSServiceFactory


class GenerateSpeechFromEntriesUseCase:
    """Use case for converting script entries to speech audio files."""

    def execute(
        self,
        script_entries: List[ScriptEntry],
        tts_config: TTSConfig,
        output_dir: Path,
    ) -> AudioScript:
        """
        Generate speech audio files from script entries.

        Args:
            script_entries: List of script entries to convert
            tts_config: TTS configuration
            output_dir: Directory to save audio files

        Returns:
            SpeechScript with audio files and timing information
        """
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create TTS service
        tts_service = TTSServiceFactory.create_service(tts_config)

        # Convert script entries to TTS requests
        tts_requests = self._create_tts_requests(script_entries)

        # Generate speech with helpful error context
        try:
            speech_script = tts_service.synthesize_script(tts_requests, output_dir)
            return speech_script
        except Exception as e:
            # Provide helpful context for TTS errors
            error_msg = str(e)

            # Collect character voice configurations for better error messages
            characters_info = []
            for entry in script_entries:
                char = entry.character
                voice_info = f"'{char.name}'"
                if char.tts_voice_clone:
                    voice_info += f" (clone: {char.tts_voice_clone})"
                elif char.tts_voice_predefined:
                    voice_info += f" (predefined: {char.tts_voice_predefined})"
                characters_info.append(voice_info)

            raise Exception(
                f"TTS generation failed: {error_msg}\n"
                f"Characters configured: {', '.join(characters_info)}\n"
            )

    def _create_tts_requests(
        self, script_entries: List[ScriptEntry]
    ) -> List[TTSRequest]:
        """Convert script entries to TTS requests."""
        requests = []

        for entry in script_entries:
            character = entry.character

            # Determine voice mode and settings from character configuration
            voice_mode = (
                VoiceMode.CLONE if character.tts_voice_clone else VoiceMode.PREDEFINED
            )
            predefined_voice_id = (
                character.tts_voice_predefined
                if voice_mode == VoiceMode.PREDEFINED
                else None
            )
            reference_audio_filename = (
                character.tts_voice_clone if voice_mode == VoiceMode.CLONE else None
            )

            # Create TTS request
            request = TTSRequest(
                text=entry.content,
                character=character,
                voice_mode=voice_mode,
                predefined_voice_id=predefined_voice_id,
                reference_audio_filename=reference_audio_filename,
                output_format=OutputFormat.WAV,  # Default to WAV
                split_text=True,
                chunk_size=120,
            )

            requests.append(request)

        return requests
