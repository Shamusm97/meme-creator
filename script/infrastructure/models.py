from dataclasses import dataclass, field


@dataclass
class ThinkingConfig:
    """Configuration for LLM thinking mode"""

    include_thoughts: bool = field(default=False)
    thinking_budget: int = field(default=0)

    def __post_init__(self):
        if not isinstance(self.include_thoughts, bool):
            raise ValueError("include_thoughts must be a boolean")
        if (
            not isinstance(self.thinking_budget, (int, float))
            or self.thinking_budget < 0
        ):
            raise ValueError("thinking_budget must be a non-negative number")
        self.thinking_budget = int(self.thinking_budget)


@dataclass
class GeminiLLMConfig:
    """Configuration specific to Gemini LLM provider"""

    temperature: float = field(default=0.7)
    max_output_tokens: int = field(default=1024)
    model: str = field(default="gemini-2.5-flash")
    direct_output: bool = field(default=False)
    thinking_config: ThinkingConfig = field(default_factory=ThinkingConfig)

    def __post_init__(self):
        if (
            not isinstance(self.temperature, (int, float))
            or not 0 <= self.temperature <= 2
        ):
            raise ValueError("Temperature must be a number between 0 and 2")
        if not isinstance(self.max_output_tokens, int) or self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Model must be a non-empty string")
        if not isinstance(self.direct_output, bool):
            raise ValueError("direct_output must be a boolean")
        if not isinstance(self.thinking_config, ThinkingConfig):
            raise ValueError("thinking_config must be a ThinkingConfig instance")
