from typing import Dict, Any


class ValidationAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        results = state.get("scenario_results", [])
        all_passed = all(r.get("passed", True) for r in results) if results else False
        state["test_passed"] = all_passed
        state["validation_completed"] = True
        return state