import os

from script.domain.models import LLMClient
from config.domain.models import LLMConfig
from script.infrastructure.gemini_client import (
    GeminiLLMClient,
    GeminiLLMConfig,
    ThinkingConfig,
)


class LLMClientFactory:
    @staticmethod
    def create_client(llm_config: LLMConfig) -> LLMClient:
        """Create LLM client from validated configuration."""
        provider = llm_config.provider.lower()

        if provider == "gemini":
            return LLMClientFactory._create_gemini_client(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def _create_gemini_client(llm_config: LLMConfig) -> GeminiLLMClient:
        """Create Gemini client from validated configuration."""
        api_key = (
            llm_config.api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        # Create provider-specific config from generic config dict
        config_dict = llm_config.config.copy()

        # Handle nested ThinkingConfig
        if "thinking_config" in config_dict:
            thinking_data = config_dict["thinking_config"]
            config_dict["thinking_config"] = ThinkingConfig(**thinking_data)

        gemini_config = GeminiLLMConfig(**config_dict)
        return GeminiLLMClient(config=gemini_config, api_key=api_key)
