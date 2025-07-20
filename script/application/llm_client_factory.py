import os
from typing import Dict, Type

from google.genai.types import GenerateContentConfig, ThinkingConfig
from script.domain.models import LLMClient, LLMConfig
from script.infrastructure.gemini_client import GeminiConfig, GeminiLLMClient


class LLMClientFactory:
    @staticmethod
    def create_client(llm_config: LLMConfig) -> LLMClient:
        """Create LLM client from raw configuration dictionary."""
        provider = llm_config.provider.lower()

        if provider == "gemini":
            return LLMClientFactory._create_gemini_client(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def _create_gemini_client(llm_config: LLMConfig) -> GeminiLLMClient:
        """Create Gemini client from raw configuration dictionary."""
        validated_config = LLMClientFactory._validate_gemini_config(llm_config)
        api_key = (
            llm_config.api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        return GeminiLLMClient(gemini_config=validated_config, api_key=api_key)

    @staticmethod
    def _validate_gemini_config(llm_config: LLMConfig) -> GeminiConfig:
        """Validate and convert raw config to GeminiConfig."""

        config = llm_config.config or {}
        # check that the config is not empty and is a dictionary
        if not isinstance(config, dict):
            raise ValueError("LLM config must be a dictionary")
        if not config:
            raise ValueError("LLM config cannot be empty")

        # Validate numeric values
        temperature = config.get("temperature", 0.7)
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("Temperature must be a number between 0 and 2")

        max_output_tokens = config.get("max_output_tokens", 1024)
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")

        model = config.get("model", "gemini-2.5-flash")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Model must be a non-empty string")

        direct_output = config.get("direct_output", False)
        if not isinstance(direct_output, bool):
            raise ValueError("direct_output must be a boolean")

        thinking_config_data = config.get("thinking_config")
        if thinking_config_data is None:
            thinking_config = ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        else:
            if not isinstance(thinking_config_data, dict):
                raise ValueError("thinking_config must be a dictionary")

            include_thoughts = thinking_config_data.get("include_thoughts", False)
            thinking_budget = thinking_config_data.get("thinking_budget", 0.0)

            if not isinstance(include_thoughts, bool):
                raise ValueError("include_thoughts must be a boolean")
            if not isinstance(thinking_budget, (int, float)) or thinking_budget < 0:
                raise ValueError("thinking_budget must be a non-negative number")

            thinking_config = ThinkingConfig(
                include_thoughts=include_thoughts,
                thinking_budget=int(thinking_budget),
            )

        return GeminiConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            model=model,
            direct_output=direct_output,
            thinking_config=thinking_config,
        )
