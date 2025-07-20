from typing import List
from config.domain.models import ScriptConfig, LLMConfig
from script.domain.models import ScriptEntry
from script.application.llm_client_factory import LLMClientFactory


class GenerateScriptUseCase:
    def execute(
        self, script_config: ScriptConfig, llm_config: LLMConfig
    ) -> List[ScriptEntry]:
        # Factory creates the right client based on provider
        llm_client = LLMClientFactory.create_client(llm_config)

        # Client handles provider-specific config validation
        return llm_client.generate_script(script_config)
