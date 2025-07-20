# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a meme creator application that generates user defined dialogue scripts, converts them to speech using TTS, and creates meme videos. The project follows a domain-driven design with clean architecture patterns.

## Development Environment

### Setup
The project uses Nix for dependency management. To enter the development environment:
```bash
nix develop
```

This provides Python 3 with required packages:
- ffmpeg-python
- moviepy  
- google-genai
- python-dotenv

### Environment Variables
Create a `.env` file with:
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` - Required for LLM script generation

## Architecture

The codebase follows a clean architecture with domain-driven design:

### Core Domains
1. **Config** (`config/`) - Shared configuration models and infrastructure
2. **Script** (`script/`) - LLM-powered dialogue generation 
3. **TTS** (`tts/`) - Text-to-speech conversion using Chatterbox API
4. **Video** (`video/`) - Video creation and editing (MoviePy integration)

### Layer Structure
Each domain follows the same pattern:
- `domain/models.py` - Core business entities and abstract interfaces
- `infrastructure/` - External service implementations (Gemini, Chatterbox, MoviePy)
- `application/` - Use cases and application services

### Key Models
- `Character` - Represents dialogue participants with voice/style settings
- `ScriptConfig` - Configuration for LLM dialogue generation
- `ScriptEntry` - Individual dialogue lines with character attribution
- `LLMClient` - Abstract interface for script generation services

## Main Workflow

The complete meme creation workflow:
1. Define characters with speaking styles, roles, and voice settings
2. Configure script generation parameters (topic, scenario, dialogue length)
3. Generate dialogue using Gemini LLM client 
4. Convert script entries to speech using Chatterbox TTS
5. Create video with character images and background using MoviePy
6. Output final meme video with synchronized audio and visuals

## Development Commands

### Running the Application

**Programmatic version:**
```bash
python main.py
```

**Config-driven version (recommended):**
```bash
python main_with_config.py
```

**Complete meme creation workflow:**
```bash
python application/meme_creation_use_case.py <config_file>
```

**Script generation only:**
```bash
python application/script_generation_use_case.py <config_file>
```

**TTS generation from existing script file:**
```bash
python tts/application/generate_speech_from_entries_use_case.py <script_file> <config_file>
```

**Script + TTS generation (orchestrated):**
```bash
python application/generate_script_and_tts_use_case.py <config_file>
```

**Video creation from TTS files:**
```bash
python video/application/create_video_use_case.py <config_file>
```

### Configuration
The application supports clean JSON configuration files with different templates in the `test/` directory:
- `test/example_config.json` - Complete meme creation workflow configuration
- `test/example_script_generation_config.json` - Script generation only
- `test/example_script_and_tts_config.json` - Script + TTS workflow

Complete structure example:

```json
{
  "project_name": "Your Project Name",
  "characters": [...],
  "script": {
    "llm": {
      "provider": "gemini",
      "gemini": {
        "temperature": 0.7,
        "max_output_tokens": 1024,
        "model": "gemini-2.5-flash",
        "thinking_config": {...}
      }
    }
  },
  "tts": {
    "provider": "chatterbox",
    "chatterbox": {
      "base_url": "http://localhost:8004",
      "endpoint": "/tts",
      "timeout": 120
    }
  },
  "video": {
    "provider": "moviepy",
    "background_video": "assets/background.mp4",
    "moviepy": {
      "quality": "medium",
      "fps": 30,
      "codec": "libx264"
    }
  }
}
```

### Configuration Workflows
Different JSON configuration templates support specific workflows:

**Full Meme Creation** (`test/example_config.json`):
- Includes script, TTS, and video configuration
- Requires character images and background video assets
- Produces complete meme video with synchronized audio

**Script Generation Only** (`test/example_script_generation_config.json`):
- Contains only script and character definitions
- Outputs JSON script entries for later processing
- Useful for dialogue generation without TTS/video

**Script + TTS** (`test/example_script_and_tts_config.json`):
- Includes script and TTS configuration
- Generates audio files from script entries
- Excludes video creation components

The script generation uses typed configuration models with built-in validation. No wrapper classes needed.

## External Dependencies

### Chatterbox TTS API
- Expected to run on localhost:8004 (default)
- Supports both predefined voices and voice cloning
- Voice profiles available in `CHATTERBOX_VOICE_PROFILES` enum
- Handles streaming audio generation and batch processing

### Google Gemini API
- Configured via `GeminiConfig` and `GeminiLLMClient`
- Supports thinking mode and direct output options
- Validates dialogue format and parses character-based scripts

## File Naming Conventions
- Models are in `domain/models.py` for each domain
- Infrastructure clients follow pattern: `{service_name}_client.py`
- Use cases follow pattern: `{action}_use_case.py`

## Clean Architecture Improvements

### Configuration Layer
- **Explicit Config Models**: Replaced generic `Dict[str, Any]` with typed models (`GeminiLLMConfig`, `ChatterboxTTSConfig`, `MoviePyVideoConfig`)
- **JSON Transparency**: Clear JSON structure visible in domain models, no hidden configuration
- **Built-in Validation**: Domain models handle their own validation in `__post_init__`
- **Configuration Loading**: Infrastructure layer (`config/infrastructure/json.py`) handles JSON serialization

### Eliminated Wrapper Classes
- Removed `GeminiConfig` wrapper class that duplicated `LLMConfig`
- All service clients now work directly with domain models
- Factories simplified to pure creation without validation logic

### Domain-Driven Design Implementation
- **Script Domain**: LLM-powered dialogue generation with clean abstractions
- **TTS Domain**: Text-to-speech with voice profiles and character-based synthesis
- **Video Domain**: Video creation with character scenes and background integration
- **Config Domain**: Shared configuration models used across all domains

### Separation of Concerns
- **Domain**: Business rules, entities, and validation in models
- **Application**: Use cases orchestrate domain logic and coordinate between domains
- **Infrastructure**: External service implementations (Gemini, Chatterbox, MoviePy) and JSON handling

## Important Notes
- All domains now follow clean DDD architecture with proper separation of concerns
- TTS infrastructure includes comprehensive voice management and character-based synthesis
- Video infrastructure fully implemented with MoviePy integration for meme creation
- Script validation ensures proper "CHARACTER:" formatting for TTS compatibility
- Complete end-to-end workflow available via `MemeCreationUseCase`
- Configuration-driven approach recommended over programmatic setup
- No test framework is currently configured
