from pathlib import Path
from dotenv import load_dotenv

from config.infrastructure.json import ConfigurationLoader
from script.application.generate_script_use_case import ScriptGenerationUseCase


def main():
    """Main application entry point using JSON configuration."""
    load_dotenv()

    # Load configuration from JSON file
    config_path = Path("./test/example_config.json")
    project_config = ConfigurationLoader.load_from_file(config_path)

    # Generate script using the use case (characters already populated in script_config)
    if not project_config.script_config:
        print("Error: Script configuration is missing from the config file")
        return
        
    use_case = ScriptGenerationUseCase()
    output_dir = project_config.base_output_dir / project_config.project_name / "scripts"
    script = use_case.execute_and_save(
        script_config=project_config.script_config,
        output_dir=output_dir,
    )

    # Output results
    print(f"Generated Script for: {project_config.project_name}")
    print("=" * 50)
    for entry in script:
        print(f"{entry.character.name}: {entry.content}")


if __name__ == "__main__":
    main()

