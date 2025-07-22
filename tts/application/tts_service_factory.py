"""Factory for creating TTS service instances."""

from config.domain.models import TTSConfig
from tts.domain.models import TTSService
from tts.infrastructure.chatterbox_client import (
    ChatterboxTTSClient,
    ChatterboxTTSConfig,
)


class TTSServiceFactory:
    """Factory for creating TTS service instances."""

    @staticmethod
    def create_service(tts_config: TTSConfig) -> TTSService:
        """Create TTS service from configuration."""
        provider = tts_config.provider.lower()

        if provider == "chatterbox":
            # Create provider-specific config from generic config dict
            chatterbox_config = ChatterboxTTSConfig(**tts_config.config)
            return ChatterboxTTSClient(chatterbox_config)
        else:
            raise ValueError(f"Unsupported TTS provider: {provider}")
