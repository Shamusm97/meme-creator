from google import genai
from google.genai.types import GenerateContentConfig, ThinkingConfig
from typing import Optional

from config.domain.models import ScriptConfig
from script.domain.models import LLMClient, Script
from script.infrastructure.models import GeminiLLMConfig
from script.infrastructure.script_repository import ScriptRepository


class GeminiLLMClient(LLMClient):
    def __init__(self, config: GeminiLLMConfig, api_key: Optional[str] = None):
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            # Will automatically pick up GEMINI_API_KEY or GOOGLE_API_KEY from environment
            # This is a double safety check, first being checked in the factory method
            self.client = genai.Client()

        self.config = config
        self.repository = ScriptRepository()

    def generate_script(
        self,
        script_config: ScriptConfig,
    ) -> Script:
        try:
            user_prompt = script_config.user_prompt.strip()

            # Configure generation parameters using stored config
            genai_config = self._create_genai_config(script_config.system_prompt)

            # Generate response
            response = self.client.models.generate_content(
                model=self.config.model, contents=user_prompt, config=genai_config
            )

            if not response or not response.text:
                raise ValueError("No content generated by the model.")

            raw_script_content = response.text.strip()
            parsed_script = self.repository.parse_script_from_string(
                script_str=raw_script_content, characters=script_config.characters
            )

            script = parsed_script

            return script

        except Exception as e:
            raise Exception(f"Error generating content: {str(e)}")

    def _create_genai_config(self, system_prompt: str) -> GenerateContentConfig:
        """Convert stored config to Google GenAI config format."""
        thinking_config = ThinkingConfig(
            include_thoughts=self.config.thinking_config.include_thoughts,
            thinking_budget=self.config.thinking_config.thinking_budget,
        )

        return GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            thinking_config=thinking_config,
        )
