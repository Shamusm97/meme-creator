from pathlib import Path
from typing import List

from config.domain.models import ScriptConfig
from config.infrastructure.json import ConfigurationLoader
from script.domain.models import ScriptEntry
from script.infrastructure.script_entries_repository import ScriptEntriesRepository
from script.application.llm_client_factory import LLMClientFactory


class ScriptGenerationUseCase:
    """Use case for generating scripts from project configuration."""

    def execute_and_save(
        self, script_config: ScriptConfig, output_dir: Path
    ) -> List[ScriptEntry]:
        """
        Generate script from ScriptConfig and save to files.

        Args:
            script_config: Script generation configuration
            output_dir: Directory to save script files

        Returns:
            List of generated script entries
        """
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate script entries
        llm_client = LLMClientFactory.create_client(script_config.llm_config)
        script_entries = llm_client.generate_script(script_config)

        # Save script entries as structured JSON
        script_json_file = output_dir / "script_entries.json"
        script_repository = ScriptEntriesRepository()
        script_repository.save_to_json_file(script_entries, script_json_file)

        return script_entries


def main():
    """Main function demonstrating script generation use case."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) != 2:
        print("Usage: python script_generation_use_case.py <config_file>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Load config
        project_config = ConfigurationLoader.load_from_file(config_path)
        script_config = project_config.script_config
        assert script_config is not None, (
            "Script configuration is missing in the project config."
        )

        output_dir = project_config.base_output_dir / project_config.project_name

        use_case = ScriptGenerationUseCase()
        script_entries = use_case.execute_and_save(
            script_config,
            output_dir,
        )

        print(f"Script Generation Results for: {project_config.project_name}")
        print("=" * 50)
        print(f" Generated {len(script_entries)} dialogue entries")

        characters = list(set(entry.character.name for entry in script_entries))
        print(f" Characters: {', '.join(characters)}")

        print(f"\nOutput Directory: {output_dir}")

        # Also display the generated dialogue
        print("\nGenerated Dialogue:")
        print("-" * 30)

        if script_entries:
            for entry in script_entries:
                print(f"{entry.character.name}: {entry.content}")
        else:
            print("No dialogue entries generated.")

    except Exception as e:
        print(f"Error generating script: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

