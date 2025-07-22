"""Refactored use case for merging audio files using AudioProcessingService."""

from pathlib import Path

from tts.domain.models import AudioScript, AudioFile
from tts.infrastructure.audio_processing_service import AudioProcessingService


class MergeAudioScriptUseCase:
    """Use case for merging multiple audio files from an AudioScript into a single file."""

    def __init__(self, audio_processing_service: AudioProcessingService = None):
        self.audio_processing_service = audio_processing_service or AudioProcessingService()

    def execute(
        self,
        audio_script: AudioScript,
        output_path: Path,
        delay_between_files: float = 0.0,
        show_progress: bool = True,
    ) -> AudioFile:
        """
        Merge all audio files in the script into a single audio file.

        Args:
            audio_script: AudioScript containing ordered audio files
            output_path: Path where the merged audio file should be saved
            delay_between_files: Seconds of silence to add between each audio file
            show_progress: Whether to display progress during merging

        Returns:
            AudioFile representing the merged audio
        """
        if not audio_script.audio_files:
            raise ValueError("AudioScript contains no audio files to merge")

        return self.audio_processing_service.merge_audio_files(
            audio_files=audio_script.audio_files,
            output_path=output_path,
            delay_between_files=delay_between_files,
            show_progress=show_progress,
        )


def main():
    """Main function demonstrating audio merging."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 3:
        print(
            "Usage: python merge_audio_script_use_case.py <audio_script_dir> <output_file>"
        )
        print(
            "       python merge_audio_script_use_case.py <audio_script_dir> <output_file> <delay_seconds>"
        )
        sys.exit(1)

    audio_script_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    delay_seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

    if not audio_script_dir.exists():
        print(f"Error: Audio script directory not found: {audio_script_dir}")
        sys.exit(1)

    try:
        # Load audio script from directory
        from tts.application.load_audio_script_use_case import LoadAudioScriptUseCase
        
        load_use_case = LoadAudioScriptUseCase()
        audio_script = load_use_case.execute(audio_script_dir)

        # Merge audio files
        merge_use_case = MergeAudioScriptUseCase()
        merged_audio = merge_use_case.execute(audio_script, output_file, delay_seconds)

        print(f"Audio Merging Results")
        print("=" * 30)
        print(f"✓ Merged {len(audio_script.audio_files)} audio files")
        print(f"✓ Total duration: {merged_audio.duration_seconds:.2f} seconds")
        print(f"✓ Output file: {merged_audio.path}")
        print(f"✓ File size: {merged_audio.file_size_bytes / 1024 / 1024:.1f} MB")

    except Exception as e:
        print(f"Error merging audio: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()