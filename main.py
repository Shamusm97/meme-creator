import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from dotenv import load_dotenv
from moviepy import *

# Import your existing modules
from script_generation.google import GoogleLLMClient, save_script
from script_generation.models import ScriptEntry, DialoguePrompt, Character
from tts.chatterbox import ChatterboxTTSClient, ChatterboxTTSRequest, CHATTERBOX_VOICE_PROFILES

@dataclass
class ProjectConfig:
    """Configuration for the video project"""
    project_name: str
    background_video: str
    character_images: Dict[str, str]  # character_name -> image_path
    output_resolution: tuple = (1920, 1080)
    fade_duration: float = 0.3

class VideoGenerationPipeline:
    def __init__(self, project_name: str):
        load_dotenv()
        self.project_name = project_name
        self.project_dir = Path(f"projects/{project_name}")
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.audio_dir = self.project_dir / "audio"
        self.scripts_dir = self.project_dir / "scripts"
        self.output_dir = self.project_dir / "output"
        
        for dir_path in [self.audio_dir, self.scripts_dir, self.output_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Initialize clients
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.llm_client = GoogleLLMClient(api_key=self.google_api_key)
        self.tts_client = ChatterboxTTSClient(base_url="http://localhost:8004")
        
        # Project data
        self.script_entries: List[ScriptEntry] = []
        self.config: ProjectConfig = None
    
    def generate_script(self, dialogue_prompt: DialoguePrompt) -> str:
        """Generate script using LLM"""
        system_prompt = dialogue_prompt.get_system_prompt()
        user_prompt = dialogue_prompt.get_user_prompt()
        
        print("=== GENERATING SCRIPT ===")
        script = self.llm_client.generate_script(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=2048,
            direct_output=True,
            model='gemini-2.5-flash'
        )
        
        # Save script
        script_path = self.scripts_dir / f"{self.project_name}_script.txt"
        save_script(script, str(script_path))
        print(f"Script saved to: {script_path}")
        
        return script
    
    def parse_script(self, script: str) -> List[ScriptEntry]:
        """Parse script into structured data"""
        print("=== PARSING SCRIPT ===")
        lines = script.split('\n')
        
        self.script_entries = []
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                character = parts[0].strip()
                dialogue = parts[1].strip()
                
                entry = ScriptEntry(
                    character=character,
                    dialogue=dialogue
                )
                self.script_entries.append(entry)
        
        print(f"Parsed {len(self.script_entries)} dialogue entries")
        return self.script_entries
    
    def generate_audio(self) -> None:
        """Generate TTS audio for each script entry"""
        print("=== GENERATING AUDIO ===")
        
        for i, entry in enumerate(self.script_entries):
            # Create TTS request
            tts_request = ChatterboxTTSRequest(
                text=entry.dialogue,
                voice_mode="clone",
                reference_audio_filename=f"{entry.character.lower()}.mp3",
                output_format="wav",
                split_text=True,
                chunk_size=120,
                voice_profile=CHATTERBOX_VOICE_PROFILES.EXPRESSIVE_MONOLOGUE.value
            )
            
            # Generate audio file
            audio_filename = f"{entry.character.lower()}_{i:03d}.wav"
            audio_path = self.audio_dir / audio_filename
            
            try:
                self.tts_client.synthesize_to_file(
                    request=tts_request,
                    output_path=str(audio_path)
                )
                
                # Update entry with audio info
                entry.audio_filename = str(audio_path)
                print(f"Generated audio: {audio_filename}")
                
            except Exception as e:
                print(f"Error generating audio for {entry.character}: {e}")
    
    def calculate_timing(self) -> None:
        """Calculate timing information for each script entry"""
        print("=== CALCULATING TIMING ===")
        
        current_time = 0.0
        
        for entry in self.script_entries:
            if entry.audio_filename and os.path.exists(entry.audio_filename):
                try:
                    # Get audio duration using moviepy
                    audio_clip = AudioFileClip(entry.audio_filename)
                    entry.duration = audio_clip.duration
                    entry.start_time = current_time
                    entry.end_time = current_time + entry.duration
                    current_time = entry.end_time
                    
                    audio_clip.close()  # Clean up
                    
                    print(f"{entry.character}: {entry.duration:.2f}s ({entry.start_time:.2f}-{entry.end_time:.2f})")
                    
                except Exception as e:
                    print(f"Error getting duration for {entry.audio_filename}: {e}")
                    entry.duration = 3.0  # Default fallback
                    entry.start_time = current_time
                    entry.end_time = current_time + entry.duration
                    current_time = entry.end_time
    
    def setup_project_config(self, background_video: str, character_images: Dict[str, str]) -> None:
        """Set up project configuration"""
        self.config = ProjectConfig(
            project_name=self.project_name,
            background_video=background_video,
            character_images=character_images
        )
        
        # Update script entries with character image paths
        for entry in self.script_entries:
            if entry.character in character_images:
                entry.character_image = character_images[entry.character]
    
    def generate_video(self) -> str:
        """Generate final video with character overlays"""
        print("=== GENERATING VIDEO ===")
        
        if not self.config:
            raise ValueError("Project config not set. Call setup_project_config() first.")
        
        # Load background video
        if os.path.exists(self.config.background_video):
            background = VideoFileClip(self.config.background_video)
        else:
            # Create colored background if no video provided
            total_duration = max([entry.end_time for entry in self.script_entries]) if self.script_entries else 10
            background = ColorClip(size=self.config.output_resolution, color=(50, 50, 50), duration=total_duration)
        
        # Collect all audio clips for the soundtrack
        audio_clips = []
        
        # Collect all video clips (background + character overlays)
        video_clips = [background]
        
        for entry in self.script_entries:
            # Add audio clip
            if entry.audio_filename and os.path.exists(entry.audio_filename):
                audio_clip = AudioFileClip(entry.audio_filename).with_start(entry.start_time)
                audio_clips.append(audio_clip)
            
            # Add character image overlay
            if entry.character_image and os.path.exists(entry.character_image):
                char_image = (ImageClip(entry.character_image, duration=entry.duration)
                            .with_start(entry.start_time)
                            .with_position('center'))
                
                video_clips.append(char_image)
        
        # Composite video
        final_video = CompositeVideoClip(video_clips)
        
        # Composite audio
        if audio_clips:
            final_audio = CompositeAudioClip(audio_clips)
            final_video = final_video.with_audio(final_audio)
        
        # Export
        output_path = self.output_dir / f"{self.project_name}_final.mp4"
        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec='libx264',
            audio_codec='aac'
        )
        
        # Cleanup
        final_video.close()
        if audio_clips:
            for clip in audio_clips:
                clip.close()
        
        print(f"Video saved to: {output_path}")
        return str(output_path)
    
    def save_project_data(self) -> None:
        """Save project data to JSON for future reference"""
        project_data = {
            "project_name": self.project_name,
            "config": asdict(self.config) if self.config else None,
            "script_entries": [asdict(entry) for entry in self.script_entries]
        }
        
        json_path = self.project_dir / f"{self.project_name}_data.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2)
        
        print(f"Project data saved to: {json_path}")
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.tts_client.session.close()

def main():
    # Get project name
    project_name = input("Enter project name: ").strip()
    if not project_name:
        project_name = "default_project"
    
    # Initialize pipeline
    pipeline = VideoGenerationPipeline(project_name)
    
    # Define dialogue parameters
    dialogue = DialoguePrompt(
        overall_conversation_style="Casual and humorous",
        main_topic="Whether or not the Jews will ascend to the third heaven. Have they already ascended? Are they already there?",
        dialogue_length="1-2 minutes",
        scenario="A light-hearted debate between two characters discussing the topic over coffee.",
        characters=[
            Character(name="Peter", role="answerer", speaking_style="casual and witty"),
            Character(name="Stewie", role="questioner", speaking_style="curious and straightforward")
        ]
    )
    
    try:
        # 1. Generate script
        script = pipeline.generate_script(dialogue)
        
        # 2. Parse script
        pipeline.parse_script(script)
        
        # 3. Generate audio
        pipeline.generate_audio()
        
        # 4. Calculate timing
        pipeline.calculate_timing()
        
        # 5. Setup project configuration
        # TODO: Replace these paths with your actual files
        character_images = {
            "Peter": "assets/Peter.png",     # Replace with actual image paths
            "Stewie": "assets/Stewie.png"    # Replace with actual image paths
        }
        background_video = "assets/background.mp4"  # Replace with actual background
        
        pipeline.setup_project_config(background_video, character_images)
        
        # 6. Generate final video
        output_video = pipeline.generate_video()
        
        # 7. Save project data
        pipeline.save_project_data()
        
        print(f"\n=== PROJECT COMPLETE ===")
        print(f"Final video: {output_video}")
        print(f"Project directory: {pipeline.project_dir}")
        
    except Exception as e:
        print(f"Error in pipeline: {e}")
    finally:
        # Cleanup
        pipeline.cleanup()

if __name__ == "__main__":
    main()