import re
import logging
from typing import Dict, Any
from .base_agent import BaseAgent

class DiagnosticAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Diagnose test failures and determine healing strategies"""
        self.logger.info("🔍 DiagnosticAgent: Analyzing test failures")
        
        # Initialize state fields
        state = {
            "orchestrator": state.get("orchestrator"),
            "config_path": state.get("config_path"),
            "user_story": state.get("user_story"),
            "logger": state.get("logger"),
            "framework_details": state.get("framework_details", {}),
            "framework_initialized": state.get("framework_initialized", False),
            "feature_path": state.get("feature_path", ""),
            "step_definitions_path": state.get("step_definitions_path", ""),
            "test_passed": state.get("test_passed", False),
            "test_executed": state.get("test_executed", False),
            "test_exec_result": state.get("test_exec_result"),
            "scenario_results": state.get("scenario_results", []),
            "needs_self_heal": False,
            "healing_attempts": state.get("healing_attempts", 0),
            "healing_types": state.get("healing_types", []),
            "syntax_healed": state.get("syntax_healed", False),
            "runtime_healed": state.get("runtime_healed", False),
            "diagnosed": True,  # This agent does the diagnosis
            "error_type": None,
            "error_details": None,
            "error_specifics": {},
            "manual_review": False,
            "validation_completed": False,
            "report_path": state.get("report_path", ""),
            "current_step": "diagnostic",
            "execution_trail": state.get("execution_trail", []),
            "max_healing_attempts": state.get("max_healing_attempts", 5),
            "enable_auto_healing": state.get("enable_auto_healing", True)
        }
        
        # Get raw test output for pattern analysis
        test_output = state.get("test_output", "")
        
        # Check for specific error patterns
        error_patterns = {
            "config_not_found": (r"No such file or directory: .*telecom_config\.json", "Configuration file not found"),
            "connection_refused": (r"Connection refused.*localhost:8000", "SMS API service not running"),
            "undefined_steps": (r"undefined.*step", "Missing step definitions"),
            "syntax_error": (r"SyntaxError", "Python syntax error in test files"),
            "assertion_error": (r"AssertionError", "Test assertion failed"),
            "import_error": (r"ImportError|ModuleNotFoundError", "Missing Python module")
        }
        
        found_errors = []
        for error_type, (pattern, desc) in error_patterns.items():
            if re.search(pattern, test_output, re.IGNORECASE):
                found_errors.append({"type": error_type, "description": desc})
        
        if found_errors:
            # Get the most critical error (config > connection > steps)
            critical_order = ["config_not_found", "connection_refused", "undefined_steps", 
                            "syntax_error", "import_error", "assertion_error"]
            for critical_type in critical_order:
                matching_errors = [e for e in found_errors if e["type"] == critical_type]
                if matching_errors:
                    primary_error = matching_errors[0]
                    state["error_type"] = primary_error["type"]
                    state["error_specifics"] = primary_error["description"]
                    state["needs_self_heal"] = True
                    state["healing_strategy"] = self._determine_healing_strategy(primary_error["type"], True)
                    state["diagnosed"] = True
                    state["healing_attempts"] = state.get("healing_attempts", 0)
                    state["healing_types"] = state.get("healing_types", [])
                    state["syntax_healed"] = False
                    state["runtime_healed"] = False
                    break
            else:
                # No errors found
                state["error_type"] = None
                state["error_specifics"] = None
                state["needs_self_heal"] = False
                state["diagnosed"] = True
                state["healing_attempts"] = state.get("healing_attempts", 0)
                state["healing_types"] = state.get("healing_types", [])
                state["syntax_healed"] = True
                state["runtime_healed"] = True
            return state  # Make sure we return the state
        
        # Check if we've exceeded retry limits
        orchestrator = state.get("orchestrator")
        if orchestrator and hasattr(orchestrator, 'retry_count') and hasattr(orchestrator, 'max_retries'):
            if orchestrator.retry_count >= orchestrator.max_retries:
                self.logger.warning(f"⚠️ Retry limit reached ({orchestrator.retry_count}/{orchestrator.max_retries})")
                state["error_type"] = "retry_limit_exceeded"
                state["error_specifics"] = f"Self-healing retry limit of {orchestrator.max_retries} reached"
                state["needs_self_heal"] = False
                state["healing_strategy"] = "manual_intervention"
                return state
        
        # Get failure analysis from test execution
        failure_analysis = state.get("failure_analysis", {})
        
        if not failure_analysis:
            self.logger.warning("⚠️ No failure analysis available")
            state["error_type"] = "unknown"
            state["error_specifics"] = "No failure analysis provided"
            state["needs_self_heal"] = True
            state["healing_strategy"] = "generic_repair"
            return state
        
        # Determine error type and specifics
        error_type = failure_analysis.get("failure_type", "unknown")
        error_specifics = failure_analysis.get("critical_issues", ["Unknown error"])
        
        # Determine if self-healing is needed
        needs_healing = failure_analysis.get("needs_healing", True)
        
        # Determine healing strategy
        if needs_healing:
            healing_strategy = failure_analysis.get("recommended_healing", "generic_repair")
        else:
            healing_strategy = "none"
        
        # Update state
        state["error_type"] = error_type
        state["error_specifics"] = error_specifics
        state["needs_self_heal"] = needs_healing
        state["healing_strategy"] = healing_strategy
        
        # Log diagnostic results
        self.logger.info(f"🔍 Diagnostic results:")
        self.logger.info(f"  - Error type: {error_type}")
        self.logger.info(f"  - Error specifics: {error_specifics}")
        self.logger.info(f"  - Needs self-healing: {needs_healing}")
        self.logger.info(f"  - Recommended strategy: {healing_strategy}")
        
        return state

    def _determine_error_severity(self, error_type: str) -> str:
        """Determine the severity level of an error"""
        critical_errors = ["ambiguous_step", "syntax", "import"]
        moderate_errors = ["assertion", "timeout"]
        
        if error_type in critical_errors:
            return "critical"
        elif error_type in moderate_errors:
            return "moderate"
        else:
            return "low"

    def _determine_healing_strategy(self, error_type: str, needs_healing: bool) -> str:
        """Determine the appropriate healing strategy"""
        if not needs_healing:
            return "none"
        
        strategy_mapping = {
            "config_not_found": "config_repair",
            "connection_refused": "service_repair",
            "undefined_steps": "step_repair",
            "ambiguous_step": "ambiguous_step_repair",
            "syntax": "syntax_repair",
            "import": "import_repair",
            "assertion": "assertion_repair",
            "timeout": "timeout_repair",
            "retry_limit_exceeded": "manual_intervention"
        }
        
        return strategy_mapping.get(error_type, "generic_repair")