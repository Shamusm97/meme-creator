"""Factory for creating video service instances."""

from config.domain.models import VideoConfig
from video.domain.models import VideoService
from video.infrastructure.moviepy_client import (
    MoviePyVideoClient,
    MoviePyVideoConfig,
    SubtitleConfig,
)


class VideoServiceFactory:
    """Factory for creating video service instances."""

    @staticmethod
    def create_service(video_config: VideoConfig) -> VideoService:
        """Create video service from configuration."""
        provider = video_config.provider.lower()

        if provider == "moviepy":
            # Create provider-specific config from generic config dict
            config_dict = video_config.config.copy()

            # Handle nested SubtitleConfig
            if "subtitles" in config_dict:
                subtitle_data = config_dict["subtitles"]
                config_dict["subtitles"] = SubtitleConfig(**subtitle_data)

            moviepy_config = MoviePyVideoConfig(**config_dict)
            return MoviePyVideoClient(moviepy_config)
        else:
            raise ValueError(f"Unsupported video provider: {provider}")

