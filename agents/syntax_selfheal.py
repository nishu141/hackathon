from typing import Dict, Any


class SyntaxSelfHealAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        details = state.get("test_exec_result", "")
        success = await orchestrator.self_heal_syntax_error(details)
        state["syntax_healed"] = success
        state["healing_attempts"] = state.get("healing_attempts", 0) + 1
        return state