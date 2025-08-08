from typing import Dict, Any


class HumanReviewAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state["manual_review"] = True
        state.setdefault("scenario_results", [])
        return state