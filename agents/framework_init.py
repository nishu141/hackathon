import os
from typing import Dict, Any


class FrameworkInitAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        details = await orchestrator.detect_existing_framework()

        if not details.get("valid"):
            ok, info = await orchestrator.initialize_framework()
            details.update(info)
            state["framework_initialized"] = ok
        else:
            state["framework_initialized"] = True

        state["framework_details"] = details
        return state