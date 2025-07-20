from config.domain.models import Character, LLMConfig, ScriptConfig
from dotenv import load_dotenv

from script.infrastructure.gemini_client import GeminiConfig, GeminiLLMClient


if __name__ == "__main__":
    load_dotenv()

    peter = Character(
        name="Peter Griffin",
        speaking_style="casual",
        conversational_role="answerer",
    )

    stewie = Character(
        name="Stewie Griffin",
        speaking_style="sarcastic",
        conversational_role="questioner",
    )

    script_config = ScriptConfig(
        system_prompt="You are a character in a Family Guy episode. Respond in character.",
        user_prompt="Peter, what do you think about Stewie's latest invention?",
        overall_conversation_style="humorous",
        main_topic="Family Guy Episode Dialogue",
        scenario="A typical Family Guy scene where Peter and Stewie are discussing a new invention.",
        dialogue_length="5-7 lines",
        characters=[peter, stewie],
    )

    llmconfig = LLMConfig(
        provider="gemini",
        config={
            "temperature": 0.7,
            "max_output_tokens": 1024,
            "model": "gemini-2.5-flash",
            "direct_output": False,
            "thinking_config": {
                "thinking_budget": 0,
            },
        },
    )

    Geminiconfig = GeminiConfig(
        temperature=llmconfig.config["temperature"],
        max_output_tokens=llmconfig.config["max_output_tokens"],
        model=llmconfig.config["model"],
        direct_output=llmconfig.config["direct_output"],
        thinking_config=llmconfig.config.get("thinking_config", {}),
    )

    client = GeminiLLMClient(
        gemini_config=llmconfig,
        api_key=None,  # Assuming the API key is set in the environment
    )
