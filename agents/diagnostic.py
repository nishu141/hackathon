from typing import Dict, Any


class DiagnosticAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        output = state.get("test_exec_result", "")
        error_type = None
        if "SyntaxError" in output or "IndentationError" in output:
            error_type = "SyntaxError"
        elif "ImportError" in output or "ModuleNotFoundError" in output:
            error_type = "ImportError"
        elif "NameError" in output or "AttributeError" in output:
            error_type = "RuntimeError"
        elif "failed" in output.lower():
            error_type = "AssertionError"

        state["diagnosed"] = True
        state["error_type"] = error_type or state.get("error_type")
        state["needs_self_heal"] = error_type is not None
        return state