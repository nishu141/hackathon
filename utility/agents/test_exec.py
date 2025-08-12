import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent


class TestExecAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def _parse_behave_output(self, output: str, return_code: int) -> List[Dict[str, Any]]:
        """Parse behave output to extract detailed scenario results."""
        results: List[Dict[str, Any]] = []
        
        # Check if behave command failed completely
        if return_code != 0:
            # Parse error output for specific failures
            error_lines = [line.strip() for line in output.splitlines() if line.strip()]
            
            # Look for specific error patterns
            if "SyntaxError" in output:
                results.append({
                    "scenario": "Framework Setup",
                    "passed": False,
                    "error_type": "SyntaxError",
                    "error_details": "Python syntax error in test files",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            elif "ImportError" in output or "ModuleNotFoundError" in output:
                results.append({
                    "scenario": "Framework Setup",
                    "passed": False,
                    "error_type": "ImportError",
                    "error_details": "Missing dependencies or import issues",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            elif "AssertionError" in output or "Assertion Failed:" in output:
                results.append({
                    "scenario": "Test Execution",
                    "passed": False,
                    "error_type": "AssertionError",
                    "error_details": "Test assertions failed",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                results.append({
                    "scenario": "Test Execution",
                    "passed": False,
                    "error_type": "ExecutionError",
                    "error_details": f"Test execution failed with return code {return_code}",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            return results
        
        # Parse successful behave output
        current_scenario = None
        for line in output.splitlines():
            line = line.strip()
            
            # Detect scenario start
            if line.startswith("Scenario:"):
                scenario_name = line.split("Scenario:", 1)[1].strip()
                current_scenario = {
                    "scenario": scenario_name,
                    "passed": True,
                    "steps": [],
                    "timestamp": datetime.now().isoformat()
                }
                results.append(current_scenario)
            
            # Detect step results
            elif line.startswith("Given ") or line.startswith("When ") or line.startswith("Then "):
                if current_scenario:
                    step_result = {
                        "step": line,
                        "status": "passed",
                        "details": ""
                    }
                    current_scenario["steps"].append(step_result)
            
            # Detect step failures
            elif line.startswith("AssertionError:") or line.startswith("Assertion Failed:") or line.startswith("Failed step:"):
                if current_scenario:
                    current_scenario["passed"] = False
                    current_scenario["error_type"] = "AssertionError"
                    current_scenario["error_details"] = line
                    # Mark the last step as failed
                    if current_scenario["steps"]:
                        current_scenario["steps"][ -1 ]["status"] = "failed"
                        current_scenario["steps"][ -1 ]["details"] = line
            
            # Detect other errors
            elif "ERROR:" in line or "FAILED:" in line:
                if current_scenario:
                    current_scenario["passed"] = False
                    current_scenario["error_type"] = "ExecutionError"
                    current_scenario["error_details"] = line
        
        # If no scenarios were parsed, create a summary result
        if not results:
            if "passed" in output.lower() and "failed" not in output.lower():
                results.append({
                    "scenario": "Overall Test Execution",
                    "passed": True,
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                results.append({
                    "scenario": "Overall Test Execution",
                    "passed": False,
                    "error_type": "UnknownError",
                    "error_details": "Could not parse test results",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
        
        return results

    def _validate_test_environment(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the test environment is properly set up."""
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        orchestrator = state["orchestrator"]
        output_dir = orchestrator.output_dir
        
        # Check if framework directories exist
        required_dirs = ["features", "steps", "support"]  # behave expects "steps" directory
        for dir_name in required_dirs:
            dir_path = os.path.join(output_dir, dir_name)
            if not os.path.exists(dir_path):
                validation_result["valid"] = False
                validation_result["issues"].append(f"Missing directory: {dir_name}")
        
        # Check if feature file exists
        feature_path = state.get("feature_path", "")
        if not feature_path or not os.path.exists(feature_path):
            validation_result["valid"] = False
            validation_result["issues"].append(f"Feature file not found: {feature_path}")
        
        # Check if step definitions exist
        steps_dir = os.path.join(output_dir, "steps")  # behave expects "steps" directory
        if os.path.exists(steps_dir):
            step_files = [f for f in os.listdir(steps_dir) if f.endswith('.py')]
            if not step_files:
                validation_result["warnings"].append("No step definition files found")
        else:
            validation_result["valid"] = False
            validation_result["issues"].append("Missing steps directory")
        
        # Check if behave is available
        try:
            import behave
            validation_result["behave_available"] = True
        except ImportError:
            validation_result["valid"] = False
            validation_result["issues"].append("behave package not available")
        
        return validation_result

    def _analyze_test_failures(self, output: str) -> Dict[str, Any]:
        """Analyze test output to determine failure patterns and healing strategies"""
        output_lower = output.lower()
        
        # Check for specific error types
        if "ambiguousstep" in output_lower or "ambiguous step" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "ambiguous_step_repair",
                "failure_type": "ambiguous_step",
                "critical_issues": ["Duplicate step definitions detected"],
                "recommendations": ["Clean up old step definition files", "Regenerate step definitions"]
            }
        elif "syntaxerror" in output_lower or "syntax error" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "syntax_repair",
                "failure_type": "syntax",
                "critical_issues": ["Generated code has syntax errors"],
                "recommendations": ["Regenerate feature and step definitions", "Validate code syntax"]
            }
        elif "importerror" in output_lower or "module not found" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "import_repair",
                "failure_type": "import",
                "critical_issues": ["Required modules not available"],
                "recommendations": ["Install missing dependencies", "Check import paths"]
            }
        elif "assertionerror" in output_lower or "assertion failed" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "assertion_repair",
                "failure_type": "assertion",
                "critical_issues": ["Test assertions are failing"],
                "recommendations": ["Review test logic", "Update step definitions"]
            }
        elif "timeout" in output_lower or "timed out" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "timeout_repair",
                "failure_type": "timeout",
                "critical_issues": ["Test execution is timing out"],
                "recommendations": ["Increase timeout limits", "Check system performance"]
            }
        elif "max retries" in output_lower or "retry limit" in output_lower:
            return {
                "needs_healing": False,
                "recommended_healing": None,
                "failure_type": "retry_limit_exceeded",
                "critical_issues": ["Self-healing retry limit reached"],
                "recommendations": ["Manual intervention required", "Review system configuration"]
            }
        else:
            return {
                "needs_healing": True,
                "recommended_healing": "generic_repair",
                "failure_type": "unknown",
                "critical_issues": ["Unknown failure pattern"],
                "recommendations": ["Generic repair attempt", "Review logs for details"]
            }

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tests and report initial results"""
        self.logger.info("🚀 TestExecAgent: Starting test execution")
        
        orchestrator = state["orchestrator"]
        feature_path = state.get("feature_path")
        
        if not feature_path:
            self.logger.error("❌ No feature path provided for test execution")
            state["test_execution_status"] = "failed"
            state["test_execution_error"] = "No feature path available"
            return state
        
        try:
            # Execute test with retry limit
            success, output = await orchestrator.execute_test(feature_path)
            
            # Always store raw output
            state["test_output"] = output
            
            # Parse scenario results from output (best-effort)
            scenario_results = self._parse_behave_output(output, 0 if success else 1)
            state["scenario_results"] = scenario_results
            
            if success:
                self.logger.info("✅ Test execution completed successfully")
                state["test_execution_status"] = "success"
                state["healing_type"] = None
            else:
                self.logger.warning("⚠️ Test execution failed, analyzing failures...")
                state["test_execution_status"] = "failed"
                
                # Analyze failures to determine healing strategy
                failure_analysis = self._analyze_test_failures(output)
                state["failure_analysis"] = failure_analysis
                
                # Set healing type based on analysis
                if failure_analysis["needs_healing"]:
                    state["healing_type"] = failure_analysis["recommended_healing"]
                    self.logger.info(f"🔧 Recommended healing: {failure_analysis['recommended_healing']}")
                    
                    if failure_analysis["critical_issues"]:
                        self.logger.error(f"🚨 Critical issues detected: {failure_analysis['critical_issues']}")
                else:
                    state["healing_type"] = None
                    self.logger.info("ℹ️ No healing required or healing not possible")
                
        except Exception as e:
            self.logger.error(f"💥 Test execution error: {e}")
            state["test_execution_status"] = "error"
            state["test_execution_error"] = str(e)
            state["healing_type"] = "generic_repair"
        
        return state