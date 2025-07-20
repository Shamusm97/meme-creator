import json
from typing import Dict, Any
from pathlib import Path

from config.domain.models import (
    ProjectConfig,
    Character,
    ScriptConfig,
    LLMConfig,
    GeminiLLMConfig,
    ThinkingConfig,
    TTSConfig,
    ChatterboxTTSConfig,
    VideoConfig,
    MoviePyVideoConfig,
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

        gemini_config = None
        if provider.lower() == "gemini" and "gemini" in llm_data:
            gemini_data = llm_data["gemini"]
            thinking_config = ThinkingConfig(
                include_thoughts=gemini_data.get("thinking_config", {}).get(
                    "include_thoughts", False
                ),
                thinking_budget=gemini_data.get("thinking_config", {}).get(
                    "thinking_budget", 0
                ),
            )

            gemini_config = GeminiLLMConfig(
                temperature=gemini_data.get("temperature", 0.7),
                max_output_tokens=gemini_data.get("max_output_tokens", 1024),
                model=gemini_data.get("model", "gemini-2.5-flash"),
                direct_output=gemini_data.get("direct_output", False),
                thinking_config=thinking_config,
            )

        return LLMConfig(
            provider=provider, gemini=gemini_config, api_key=llm_data.get("api_key", "")
        )

    @staticmethod
    def _load_tts_config(tts_data: Dict[str, Any]) -> TTSConfig:
        """Load TTS configuration from data."""
        provider = tts_data["provider"]

        chatterbox_config = None
        if provider.lower() == "chatterbox" and "chatterbox" in tts_data:
            chatterbox_data = tts_data["chatterbox"]
            chatterbox_config = ChatterboxTTSConfig(
                base_url=chatterbox_data["base_url"],
                endpoint=chatterbox_data.get("endpoint", "/tts"),
                timeout=chatterbox_data.get("timeout", 120),
            )

        return TTSConfig(provider=provider, chatterbox=chatterbox_config)

    @staticmethod
    def _load_video_config(video_data: Dict[str, Any]) -> VideoConfig:
        """Load video configuration from data."""
        provider = video_data.get("provider", "moviepy")

        moviepy_config = None
        if provider.lower() == "moviepy":
            moviepy_data = video_data.get("moviepy", {})
            moviepy_config = MoviePyVideoConfig(
                quality=moviepy_data.get("quality", "medium"),
                fps=moviepy_data.get("fps", 30),
                codec=moviepy_data.get("codec", "libx264"),
            )

        return VideoConfig(
            provider=provider,
            background_video=Path(video_data["background_video"]),
            moviepy=moviepy_config,
        )


class ConfigurationSerializer:
    """Serializes configuration to JSON format."""

    @staticmethod
    def to_dict(config: ProjectConfig) -> Dict[str, Any]:
        """Convert ProjectConfig to dictionary for JSON serialization."""
        return {
            "project_name": config.project_name,
            "characters": [
                ConfigurationSerializer._character_to_dict(char)
                for char in config.character_config
            ],
            "script": ConfigurationSerializer._script_config_to_dict(
                config.script_config
            ),
            "tts": ConfigurationSerializer._tts_config_to_dict(config.tts_config),
            "video": ConfigurationSerializer._video_config_to_dict(config.video_config),
        }

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

        if hasattr(script_config, "llm_config"):
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

        if llm_config.gemini:
            result["gemini"] = {
                "temperature": llm_config.gemini.temperature,
                "max_output_tokens": llm_config.gemini.max_output_tokens,
                "model": llm_config.gemini.model,
                "direct_output": llm_config.gemini.direct_output,
                "thinking_config": {
                    "include_thoughts": llm_config.gemini.thinking_config.include_thoughts,
                    "thinking_budget": llm_config.gemini.thinking_config.thinking_budget,
                },
            }

        return result

    @staticmethod
    def _tts_config_to_dict(tts_config: TTSConfig) -> Dict[str, Any]:
        """Convert TTSConfig to dictionary."""
        result: Dict[str, Any] = {"provider": tts_config.provider}

        if tts_config.chatterbox:
            result["chatterbox"] = {
                "base_url": tts_config.chatterbox.base_url,
                "endpoint": tts_config.chatterbox.endpoint,
                "timeout": tts_config.chatterbox.timeout,
            }

        return result

    @staticmethod
    def _video_config_to_dict(video_config: VideoConfig) -> Dict[str, Any]:
        """Convert VideoConfig to dictionary."""
        result: Dict[str, Any] = {
            "provider": video_config.provider,
            "background_video": str(video_config.background_video),
        }

        if video_config.moviepy:
            result["moviepy"] = {
                "quality": video_config.moviepy.quality,
                "fps": video_config.moviepy.fps,
                "codec": video_config.moviepy.codec,
            }

        return result

    @staticmethod
    def save_to_file(config: ProjectConfig, file_path: Path) -> None:
        """Save configuration to JSON file."""
        data = ConfigurationSerializer.to_dict(config)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
