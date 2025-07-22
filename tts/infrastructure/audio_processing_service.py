import subprocess
import json
from pathlib import Path
from typing import List
import tempfile

from tts.domain.models import AudioFile, AudioScript
from tts.infrastructure.audio_script_repository import AudioScriptRepository


class AudioProcessingService:
    """Service for audio processing operations using ffmpeg."""

    def __init__(self):
        self.repository = AudioScriptRepository()

    def merge_audio_files_from_directory(
        self,
        audio_dir: Path,
        output_path: Path,
        delay_between_files: float = 0.0,
        show_progress: bool = True,
    ) -> AudioFile:
        """
        Merge audio files from directory with automatic metadata discovery.

        Tries to load metadata in order: JSON -> SRT -> basic file discovery

        Args:
            audio_dir: Directory containing audio files and optional metadata
            output_path: Path where merged file should be saved
            delay_between_files: Seconds of silence between files
            show_progress: Whether to show progress messages

        Returns:
            AudioFile representing the merged result
        """
        # Try to load with metadata fallback
        audio_script = self.repository.load_audio_script_with_fallback(audio_dir)

        if audio_script:
            if show_progress:
                print(
                    f"📋 Found metadata for {len(audio_script.audio_files)} audio files"
                )
            return self.merge_audio_files(
                audio_script.audio_files,
                output_path,
                delay_between_files,
                show_progress,
            )
        else:
            # Fallback to basic file discovery
            if show_progress:
                print("⚠️  No metadata found, using basic file discovery")
            audio_script = self.repository.load_audio_script_from_directory(audio_dir)
            return self.merge_audio_files(
                audio_script.audio_files,
                output_path,
                delay_between_files,
                show_progress,
            )

    def merge_audio_files(
        self,
        audio_files: List[AudioFile],
        output_path: Path,
        delay_between_files: float = 0.0,
        show_progress: bool = True,
    ) -> AudioFile:
        """
        Merge multiple audio files into a single file.

        Args:
            audio_files: List of audio files to merge
            output_path: Path where merged file should be saved
            delay_between_files: Seconds of silence between files
            show_progress: Whether to show progress messages

        Returns:
            AudioFile representing the merged result

        Raises:
            ValueError: If no audio files provided
            Exception: If ffmpeg operation fails
        """
        if not audio_files:
            raise ValueError("No audio files provided for merging")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temporary file list for ffmpeg
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            file_list_path = Path(f.name)

        try:
            # Generate ffmpeg concat file list
            self._create_concat_file_list(
                audio_files, file_list_path, delay_between_files
            )

            # Run ffmpeg to concatenate files
            self._run_ffmpeg_concat(file_list_path, output_path, show_progress)

            # Calculate metadata
            total_duration = self._calculate_total_duration(
                audio_files, delay_between_files
            )
            file_size = output_path.stat().st_size if output_path.exists() else 0

            return AudioFile(
                path=output_path,
                script_entry=None,
                duration_seconds=total_duration,
                file_size_bytes=file_size,
            )

        finally:
            # Clean up temporary file
            if file_list_path.exists():
                file_list_path.unlink()

    def create_silence_file(
        self,
        duration_seconds: float,
        output_path: Path,
        sample_rate: int = 44100,
        channels: int = 2,
    ) -> AudioFile:
        """
        Create an audio file with silence.

        Args:
            duration_seconds: Duration of silence
            output_path: Where to save the silence file
            sample_rate: Audio sample rate
            channels: Number of audio channels

        Returns:
            AudioFile representing the silence

        Raises:
            Exception: If ffmpeg operation fails
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=duration={duration_seconds}:sample_rate={sample_rate}:channel_layout={'stereo' if channels == 2 else 'mono'}",
            "-y",  # Overwrite output
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            file_size = output_path.stat().st_size if output_path.exists() else 0

            return AudioFile(
                path=output_path,
                script_entry=None,
                duration_seconds=duration_seconds,
                file_size_bytes=file_size,
            )

        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg failed to create silence file: {e.stderr}")
        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install ffmpeg.")

    def get_audio_info(self, audio_path: Path) -> dict:
        """
        Get detailed audio file information using ffprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with audio information

        Raises:
            Exception: If ffprobe operation fails
        """
        if not audio_path.exists():
            raise Exception(f"Audio file not found: {audio_path}")

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(audio_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return json.loads(result.stdout)

        except subprocess.CalledProcessError as e:
            raise Exception(f"FFprobe failed: {e.stderr}")
        except FileNotFoundError:
            raise Exception("FFprobe not found. Please install ffmpeg.")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse ffprobe output: {e}")

    def convert_audio_format(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str = "wav",
        quality: str = "high",
    ) -> AudioFile:
        """
        Convert audio file to different format.

        Args:
            input_path: Source audio file
            output_path: Destination path
            output_format: Target format (wav, mp3, opus, etc.)
            quality: Quality level (high, medium, low)

        Returns:
            AudioFile representing converted audio

        Raises:
            Exception: If conversion fails
        """
        if not input_path.exists():
            raise Exception(f"Input audio file not found: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command based on format and quality
        cmd = ["ffmpeg", "-i", str(input_path)]

        if output_format.lower() == "mp3":
            quality_map = {"high": "192k", "medium": "128k", "low": "96k"}
            cmd.extend(["-codec:a", "mp3", "-b:a", quality_map.get(quality, "128k")])
        elif output_format.lower() == "opus":
            quality_map = {"high": "128k", "medium": "96k", "low": "64k"}
            cmd.extend(["-codec:a", "libopus", "-b:a", quality_map.get(quality, "96k")])
        elif output_format.lower() == "wav":
            cmd.extend(["-codec:a", "pcm_s16le"])

        cmd.extend(["-y", str(output_path)])  # Overwrite output

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Get file info
            file_size = output_path.stat().st_size if output_path.exists() else 0

            # Try to get duration
            try:
                audio_info = self.get_audio_info(output_path)
                duration = float(audio_info.get("format", {}).get("duration", 0))
            except Exception:
                duration = None

            return AudioFile(
                path=output_path,
                script_entry=None,
                duration_seconds=duration,
                file_size_bytes=file_size,
            )

        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg conversion failed: {e.stderr}")
        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install ffmpeg.")

    def _create_concat_file_list(
        self,
        audio_files: List[AudioFile],
        file_list_path: Path,
        delay_between_files: float,
    ) -> None:
        """Create ffmpeg concat file list with optional delays."""
        with open(file_list_path, "w", encoding="utf-8") as f:
            for i, audio_file in enumerate(audio_files):
                # Add the audio file
                f.write(f"file '{audio_file.path.absolute()}'\n")

                # Add delay between files (except after the last file)
                if delay_between_files > 0 and i < len(audio_files) - 1:
                    # Create a silent audio segment using ffmpeg's anullsrc filter
                    f.write(
                        f"file 'anullsrc=duration={delay_between_files}:sample_rate=44100:channel_layout=stereo'\n"
                    )

    def _run_ffmpeg_concat(
        self, file_list_path: Path, output_path: Path, show_progress: bool = True
    ) -> None:
        """Run ffmpeg to concatenate audio files."""
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(file_list_path),
            "-c",
            "copy",
            "-y",  # Overwrite output file
            str(output_path),
        ]

        if show_progress:
            file_count = len(
                [
                    line
                    for line in file_list_path.read_text().splitlines()
                    if line.strip() and not line.startswith("#")
                ]
            )
            print(f"🎵 Merging {file_count} audio files...")

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            if show_progress:
                print("✓ Audio merging completed")

        except subprocess.CalledProcessError as e:
            raise Exception(
                f"FFmpeg failed to merge audio files: {e.stderr}\n"
                f"Command: {' '.join(cmd)}"
            )
        except FileNotFoundError:
            raise Exception(
                "FFmpeg not found. Please install ffmpeg to merge audio files."
            )

    def _calculate_total_duration(
        self, audio_files: List[AudioFile], delay_between_files: float
    ) -> float:
        """Calculate total duration including delays."""
        total_duration = sum(
            audio_file.duration_seconds or 0 for audio_file in audio_files
        )

        # Add delays (one less delay than number of files)
        if len(audio_files) > 1:
            total_duration += delay_between_files * (len(audio_files) - 1)

        return total_duration

    def _create_merged_dialogue_string(self, audio_script: AudioScript) -> str:
        """Create a merged dialogue string from all audio files."""
        dialogue_parts = []
        for audio_file in audio_script.audio_files:
            if audio_file.script_entry and audio_file.script_entry.content.strip():
                dialogue_parts.append(audio_file.script_entry.content.strip())

        return " ".join(dialogue_parts)
