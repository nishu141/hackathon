from typing import Dict, Any


class ReportAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        results = state.get("scenario_results", [])
        report_path = await orchestrator.generate_report(results)
        state["report_path"] = report_path
        return state