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
            "ambiguous_step": "ambiguous_step_repair",
            "syntax": "syntax_repair",
            "import": "import_repair",
            "assertion": "assertion_repair",
            "timeout": "timeout_repair",
            "retry_limit_exceeded": "manual_intervention"
        }
        
        return strategy_mapping.get(error_type, "generic_repair")