"""Factory for creating video service instances."""

from config.domain.models import VideoConfig
from video.domain.models import VideoService
from video.infrastructure.moviepy_client import MoviePyVideoClient


class VideoServiceFactory:
    """Factory for creating video service instances."""
    
    @staticmethod
    def create_service(video_config: VideoConfig) -> VideoService:
        """Create video service from configuration."""
        provider = video_config.provider.lower()
        
        if provider == "moviepy":
            moviepy_config = video_config.get_provider_config()
            return MoviePyVideoClient(moviepy_config)
        else:
            raise ValueError(f"Unsupported video provider: {provider}")