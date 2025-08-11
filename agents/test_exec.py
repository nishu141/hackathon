import os
import re
import json
from typing import Dict, Any, List
from datetime import datetime


class TestExecAgent:
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
                        current_scenario["steps"][-1]["status"] = "failed"
                        current_scenario["steps"][-1]["details"] = line
            
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

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tests with robust error handling and validation."""
        print("🧪 TestExecAgent: Starting test execution...")
        
        # Validate test environment first
        validation = self._validate_test_environment(state)
        if not validation["valid"]:
            print(f"❌ TestExecAgent: Environment validation failed: {validation['issues']}")
            state["test_executed"] = False
            state["test_passed"] = False
            state["test_exec_result"] = f"Environment validation failed: {validation['issues']}"
            state["scenario_results"] = [{
                "scenario": "Environment Validation",
                "passed": False,
                "error_type": "ValidationError",
                "error_details": f"Test environment issues: {', '.join(validation['issues'])}",
                "timestamp": datetime.now().isoformat()
            }]
            state["needs_self_heal"] = True
            return state
        
        if validation["warnings"]:
            print(f"⚠️ TestExecAgent: Environment warnings: {validation['warnings']}")
        
        # Execute tests
        orchestrator = state["orchestrator"]
        feature_path = state.get("feature_path", "")
        
        print(f"🧪 TestExecAgent: Executing tests from: {feature_path}")
        
        try:
            ok, output = await orchestrator.execute_test(feature_path)
            print(f"🧪 TestExecAgent: Test execution completed. Success: {ok}")
            
            # Parse the output for detailed results
            scenario_results = self._parse_behave_output(output, 0 if ok else 1)
            
            # Update state
            state["test_executed"] = True
            state["test_exec_result"] = output
            state["scenario_results"] = scenario_results
            
            # Determine overall test status
            if scenario_results:
                all_passed = all(result.get("passed", False) for result in scenario_results)
                state["test_passed"] = all_passed
                
                # Check if self-healing is needed
                failed_scenarios = [r for r in scenario_results if not r.get("passed", True)]
                if failed_scenarios:
                    state["needs_self_heal"] = True
                    state["healing_attempts"] = state.get("healing_attempts", 0) + 1
                    
                    # Log detailed failure information
                    print(f"❌ TestExecAgent: {len(failed_scenarios)} scenarios failed:")
                    for scenario in failed_scenarios:
                        print(f"  - {scenario['scenario']}: {scenario.get('error_details', 'Unknown error')}")
                else:
                    print("✅ TestExecAgent: All scenarios passed successfully!")
            else:
                state["test_passed"] = False
                state["needs_self_heal"] = True
                print("❌ TestExecAgent: No test results generated")
            
            return state
            
        except Exception as e:
            print(f"❌ TestExecAgent: Test execution failed with exception: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            
            state["test_executed"] = False
            state["test_passed"] = False
            state["test_exec_result"] = f"Test execution exception: {str(e)}\n{error_details}"
            state["scenario_results"] = [{
                "scenario": "Test Execution",
                "passed": False,
                "error_type": "ExecutionException",
                "error_details": str(e),
                "traceback": error_details,
                "timestamp": datetime.now().isoformat()
            }]
            state["needs_self_heal"] = True
            state["healing_attempts"] = state.get("healing_attempts", 0) + 1
            
            return state