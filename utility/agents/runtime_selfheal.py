from typing import Dict, Any


class RuntimeSelfHealAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        details = state.get("test_exec_result", "")
        success = await orchestrator.self_heal_runtime_error(details)
        state["runtime_healed"] = success
        state["healing_attempts"] = state.get("healing_attempts", 0) + 1
        state["last_healed_error"] = state.get("error_type", "")
        return state