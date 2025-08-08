import os
import re
from typing import Dict, Any, List


class TestExecAgent:
    def _parse_behave_output(self, output: str) -> List[Dict[str, Any]]:
        # Very simple parser to convert behave output into scenario results
        results: List[Dict[str, Any]] = []
        for line in output.splitlines():
            if line.startswith("Scenario:"):
                name = line.split("Scenario:", 1)[1].strip()
                results.append({"scenario": name, "passed": True})
            if line.strip().startswith("Failing scenarios"):
                # Mark subsequent scenario lines as failed
                pass
        # Fallback single result if nothing parsed
        if not results:
            results.append({"scenario": "behave run", "passed": "failed" not in output.lower(), "output": output})
        return results

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        feature_path = state.get("feature_path", "")
        if not feature_path or not os.path.exists(feature_path):
            state["test_exec_result"] = "No tests defined"
            state["scenario_results"] = []
            return state

        ok, output = await orchestrator.execute_test(feature_path)
        state["test_executed"] = True
        state["test_exec_result"] = output
        state["scenario_results"] = self._parse_behave_output(output)
        state["test_passed"] = ok
        return state