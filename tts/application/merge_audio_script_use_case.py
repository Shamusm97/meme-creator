import subprocess
from pathlib import Path
from typing import Optional

from tts.domain.models import AudioScript, AudioFile
from config.domain.models import Character


class MergeAudioScriptUseCase:
    """Use case for merging multiple audio files from an AudioScript into a single file."""

    def execute(
        self,
        audio_script: AudioScript,
        output_path: Path,
        delay_between_files: float = 0.0,
    ) -> AudioFile:
        """
        Merge all audio files in the script into a single audio file.

        Args:
            audio_script: AudioScript containing ordered audio files
            output_path: Path where the merged audio file should be saved
            delay_between_files: Seconds of silence to add between each audio file

        Returns:
            AudioFile representing the merged audio
        """
        if not audio_script.audio_files:
            raise ValueError("AudioScript contains no audio files to merge")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temporary file list for ffmpeg
        file_list_path = output_path.parent / f"{output_path.stem}_filelist.txt"
        
        try:
            # Generate ffmpeg concat file list
            self._create_concat_file_list(
                audio_script.audio_files, file_list_path, delay_between_files
            )

            # Run ffmpeg to concatenate files
            self._run_ffmpeg_concat(file_list_path, output_path)

            # Calculate total duration and file size
            total_duration = self._calculate_total_duration(
                audio_script.audio_files, delay_between_files
            )
            file_size = output_path.stat().st_size if output_path.exists() else 0

            # Create merged dialogue text
            merged_dialogue = self._create_merged_dialogue(audio_script.audio_files)

            # Create a representative character (use first character or create a composite)
            representative_character = self._get_representative_character(
                audio_script.audio_files
            )

            return AudioFile(
                path=output_path,
                character=representative_character,
                dialogue=merged_dialogue,
                duration_seconds=total_duration,
                file_size_bytes=file_size,
            )

        finally:
            # Clean up temporary file list
            if file_list_path.exists():
                file_list_path.unlink()

    def _create_concat_file_list(
        self,
        audio_files: list[AudioFile],
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
                    f.write(f"file 'anullsrc=duration={delay_between_files}:sample_rate=44100:channel_layout=stereo'\n")

    def _run_ffmpeg_concat(self, file_list_path: Path, output_path: Path) -> None:
        """Run ffmpeg to concatenate audio files."""
        try:
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(file_list_path),
                "-c", "copy",
                "-y",  # Overwrite output file
                str(output_path),
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            
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
        self, audio_files: list[AudioFile], delay_between_files: float
    ) -> float:
        """Calculate total duration including delays."""
        total_duration = sum(
            audio_file.duration_seconds or 0 for audio_file in audio_files
        )
        
        # Add delays (one less delay than number of files)
        if len(audio_files) > 1:
            total_duration += delay_between_files * (len(audio_files) - 1)
        
        return total_duration

    def _create_merged_dialogue(self, audio_files: list[AudioFile]) -> str:
        """Create a merged dialogue string from all audio files."""
        dialogue_parts = []
        for audio_file in audio_files:
            character_name = audio_file.character.name
            dialogue_parts.append(f"{character_name}: {audio_file.dialogue}")
        
        return "\n".join(dialogue_parts)

    def _get_representative_character(self, audio_files: list[AudioFile]) -> Character:
        """Get a representative character for the merged audio file."""
        if not audio_files:
            raise ValueError("No audio files provided")
        
        # Use the first character as the representative
        # In the future, this could be enhanced to create a "Merged" character
        return audio_files[0].character


def main():
    """Main function demonstrating audio merging."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 3:
        print("Usage: python merge_audio_script_use_case.py <audio_script_dir> <output_file>")
        print("       python merge_audio_script_use_case.py <audio_script_dir> <output_file> <delay_seconds>")
        sys.exit(1)

    audio_script_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    delay_seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

    if not audio_script_dir.exists():
        print(f"Error: Audio script directory not found: {audio_script_dir}")
        sys.exit(1)

    try:
        # For demonstration, we'd need to load an AudioScript from the directory
        # This would typically be done by a repository or loader
        print(f"Would merge audio files from {audio_script_dir} to {output_file}")
        print(f"Delay between files: {delay_seconds} seconds")
        
        # Example usage:
        # use_case = MergeAudioScriptUseCase()
        # merged_audio = use_case.execute(audio_script, output_file, delay_seconds)
        # print(f"✓ Merged audio saved to: {merged_audio.path}")

    except Exception as e:
        print(f"Error merging audio: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()