import json
from typing import Dict, Any
from pathlib import Path

from config.domain.models import (
    ProjectConfig,
    Character,
    ScriptConfig,
    LLMConfig,
    TTSConfig,
    VideoConfig,
)


class ConfigurationLoader:
    """Loads and validates configuration from JSON files."""

    @staticmethod
    def load_from_file(file_path: Path) -> ProjectConfig:
        """Load configuration from JSON file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ConfigurationLoader.from_dict(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ProjectConfig:
        """Create ProjectConfig from dictionary."""
        # Load characters first since other configs depend on them
        characters = None
        if "characters" in data and data["characters"]:
            characters = ConfigurationLoader._load_characters(data["characters"])

        # Load optional configs only if they exist in the data
        script_config = None
        if "script" in data and data["script"]:
            script_config = ConfigurationLoader._load_script_config(
                data["script"], characters or []
            )

        tts_config = None
        if "tts" in data and data["tts"]:
            tts_config = ConfigurationLoader._load_tts_config(data["tts"])

        video_config = None
        if "video" in data and data["video"]:
            video_config = ConfigurationLoader._load_video_config(data["video"])

        return ProjectConfig(
            project_name=data["project_name"],
            base_output_dir=Path(data["base_output_dir"]),
            character_config=characters,
            script_config=script_config,
            tts_config=tts_config,
            video_config=video_config,
        )

    @staticmethod
    def _load_characters(characters_data: list) -> list[Character]:
        """Load characters from configuration data."""
        if not characters_data:
            return []

        characters = []
        for char_data in characters_data:
            character = Character(
                name=char_data["name"],
                speaking_style=char_data.get("speaking_style", ""),
                conversational_role=char_data.get("conversational_role", ""),
                image_path=Path(char_data.get("image_path", "")),
                tts_voice_clone=char_data.get("tts_voice_clone", ""),
                tts_voice_predefined=char_data.get("tts_voice_predefined", ""),
                tts_voice_profile=char_data.get("tts_voice_profile", ""),
                tts_voice_profile_overrides=char_data.get(
                    "tts_voice_profile_overrides", {}
                ),
            )
            characters.append(character)
        return characters

    @staticmethod
    def _load_script_config(
        script_data: Dict[str, Any], characters: list[Character]
    ) -> ScriptConfig:
        """Load script configuration from data with characters populated."""
        llm_config = ConfigurationLoader._load_llm_config(script_data["llm"])

        return ScriptConfig(
            overall_conversation_style=script_data["overall_conversation_style"],
            main_topic=script_data["main_topic"],
            scenario=script_data["scenario"],
            dialogue_length=script_data["dialogue_length"],
            characters=characters,  # Populated from top-level character_config
            system_prompt_extra=script_data.get("system_prompt_extra", ""),
            user_prompt_extra=script_data.get("user_prompt_extra", ""),
            llm_config=llm_config,
        )

    @staticmethod
    def _load_llm_config(llm_data: Dict[str, Any]) -> LLMConfig:
        """Load LLM configuration from data."""
        provider = llm_data["provider"]
        config = {}

        # Extract provider-specific config
        config = llm_data[provider.lower()]

        # Check that the config is not empty
        if not config:
            raise ValueError(f"Configuration for provider '{provider}' is empty.")

        return LLMConfig(
            provider=provider, config=config, api_key=llm_data.get("api_key", "")
        )

    @staticmethod
    def _load_tts_config(tts_data: Dict[str, Any]) -> TTSConfig:
        """Load TTS configuration from data."""
        provider = tts_data["provider"]

        # Extract provider-specific config
        config = tts_data[provider.lower()]

        if not config:
            raise ValueError(f"Configuration for provider '{provider}' is empty.")

        return TTSConfig(provider=provider, config=config)

    @staticmethod
    def _load_video_config(video_data: Dict[str, Any]) -> VideoConfig:
        """Load video configuration from data."""
        provider = video_data.get("provider", "moviepy")

        # Extract provider-specific config
        config = video_data[provider.lower()]

        if not config:
            raise ValueError(f"Configuration for provider '{provider}' is empty.")

        return VideoConfig(
            provider=provider,
            background_video=Path(video_data["background_video"]),
            config=config,
        )


class ConfigurationSerializer:
    """Serializes configuration to JSON format."""

    @staticmethod
    def to_dict(config: ProjectConfig) -> Dict[str, Any]:
        """Convert ProjectConfig to dictionary for JSON serialization."""
        result: Dict[str, Any] = {
            "project_name": config.project_name,
            "base_output_dir": str(config.base_output_dir),
        }

        # Add optional sections only if they exist
        if config.character_config:
            result["characters"] = [
                ConfigurationSerializer._character_to_dict(char)
                for char in config.character_config
            ]

        if config.script_config:
            result["script"] = ConfigurationSerializer._script_config_to_dict(
                config.script_config
            )

        if config.tts_config:
            result["tts"] = ConfigurationSerializer._tts_config_to_dict(
                config.tts_config
            )

        if config.video_config:
            result["video"] = ConfigurationSerializer._video_config_to_dict(
                config.video_config
            )

        return result

    @staticmethod
    def _character_to_dict(character: Character) -> Dict[str, Any]:
        """Convert Character to dictionary."""
        return {
            "name": character.name,
            "speaking_style": character.speaking_style,
            "conversational_role": character.conversational_role,
            "image_path": str(character.image_path),
            "tts_voice_clone": character.tts_voice_clone,
            "tts_voice_predefined": character.tts_voice_predefined,
            "tts_voice_profile": character.tts_voice_profile,
            "tts_voice_profile_overrides": character.tts_voice_profile_overrides,
        }

    @staticmethod
    def _script_config_to_dict(script_config: ScriptConfig) -> Dict[str, Any]:
        """Convert ScriptConfig to dictionary."""
        result: Dict[str, Any] = {
            "overall_conversation_style": script_config.overall_conversation_style,
            "main_topic": script_config.main_topic,
            "scenario": script_config.scenario,
            "dialogue_length": script_config.dialogue_length,
            "system_prompt_extra": script_config.system_prompt_extra,
            "user_prompt_extra": script_config.user_prompt_extra,
        }

        result["llm"] = ConfigurationSerializer._llm_config_to_dict(
            script_config.llm_config
        )

        return result

    @staticmethod
    def _llm_config_to_dict(llm_config: LLMConfig) -> Dict[str, Any]:
        """Convert LLMConfig to dictionary."""
        result: Dict[str, Any] = {
            "provider": llm_config.provider,
            "api_key": llm_config.api_key,
        }

        # Add provider-specific config if present
        if llm_config.config and llm_config.provider.lower() == "gemini":
            result["gemini"] = llm_config.config

        return result

    @staticmethod
    def _tts_config_to_dict(tts_config: TTSConfig) -> Dict[str, Any]:
        """Convert TTSConfig to dictionary."""
        result: Dict[str, Any] = {"provider": tts_config.provider}

        # Add provider-specific config if present
        if tts_config.config and tts_config.provider.lower() == "chatterbox":
            result["chatterbox"] = tts_config.config

        return result

    @staticmethod
    def _video_config_to_dict(video_config: VideoConfig) -> Dict[str, Any]:
        """Convert VideoConfig to dictionary."""
        result: Dict[str, Any] = {
            "provider": video_config.provider,
            "background_video": str(video_config.background_video),
        }

        # Add provider-specific config if present
        if video_config.config and video_config.provider.lower() == "moviepy":
            result["moviepy"] = video_config.config

        return result

    @staticmethod
    def save_to_file(config: ProjectConfig, file_path: Path) -> None:
        """Save configuration to JSON file."""
        data = ConfigurationSerializer.to_dict(config)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
