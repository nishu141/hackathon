from typing import Dict, Any


class ReportAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        results = state.get("scenario_results", [])
        # Generate Markdown report
        report_path = await orchestrator.generate_report(results)
        state["report_path"] = report_path
        # Generate HTML report
        html_report_path = await orchestrator.generate_html_report(results, state.get("test_output", ""))
        state["html_report_path"] = html_report_path
        return state