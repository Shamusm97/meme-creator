import os

from script.domain.models import LLMClient
from config.domain.models import LLMConfig
from script.infrastructure.gemini_client import GeminiLLMClient


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

        gemini_config = llm_config.get_provider_config()
        return GeminiLLMClient(config=gemini_config, api_key=api_key)
