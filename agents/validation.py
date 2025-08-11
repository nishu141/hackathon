import os
from typing import Dict, Any


class ValidationAgent:
    def _validate_test_results(self, scenario_results: list) -> Dict[str, Any]:
        """Validate test results and determine if execution should continue."""
        validation = {
            "valid": True,
            "critical_failures": [],
            "warnings": [],
            "should_continue": True,
            "exit_code": 0
        }
        
        if not scenario_results:
            validation["valid"] = False
            validation["critical_failures"].append("No test results generated")
            validation["should_continue"] = False
            validation["exit_code"] = 1
            return validation
        
        # Check for critical failures
        for result in scenario_results:
            if not result.get("passed", True):
                error_type = result.get("error_type", "Unknown")
                error_details = result.get("error_details", "No details provided")
                
                # Critical errors that should stop execution
                if error_type in ["SyntaxError", "ImportError", "FileSystemError", "ValidationError"]:
                    validation["critical_failures"].append(f"{error_type}: {error_details}")
                    validation["should_continue"] = False
                    validation["exit_code"] = 1
                
                # Warnings that allow execution to continue
                elif error_type in ["AssertionError", "RuntimeError", "TestFailure"]:
                    validation["warnings"].append(f"{error_type}: {error_details}")
        
        # Determine overall validation status
        if validation["critical_failures"]:
            validation["valid"] = False
        elif validation["warnings"]:
            validation["valid"] = False
            validation["should_continue"] = True  # Continue with warnings
        
        return validation

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate test execution results and determine next steps."""
        print("✅ ValidationAgent: Starting test result validation...")
        
        scenario_results = state.get("scenario_results", [])
        test_executed = state.get("test_executed", False)
        
        if not test_executed:
            print("❌ ValidationAgent: Tests were not executed")
            state["validation_completed"] = True
            state["validation_result"] = {
                "valid": False,
                "critical_failures": ["Tests were not executed"],
                "should_continue": False,
                "exit_code": 1
            }
            return state
        
        if not scenario_results:
            print("❌ ValidationAgent: No test results to validate")
            state["validation_completed"] = True
            state["validation_result"] = {
                "valid": False,
                "critical_failures": ["No test results generated"],
                "should_continue": False,
                "exit_code": 1
            }
            return state
        
        # Validate test results
        validation_result = self._validate_test_results(scenario_results)
        
        # Log validation results
        print(f"✅ ValidationAgent: Validation completed. Valid: {validation_result['valid']}")
        
        if validation_result["critical_failures"]:
            print("❌ ValidationAgent: Critical failures detected:")
            for failure in validation_result["critical_failures"]:
                print(f"  - {failure}")
        
        if validation_result["warnings"]:
            print("⚠️ ValidationAgent: Warnings detected:")
            for warning in validation_result["warnings"]:
                print(f"  - {warning}")
        
        if validation_result["should_continue"]:
            print("✅ ValidationAgent: Execution can continue")
        else:
            print("❌ ValidationAgent: Execution should stop due to critical failures")
        
        # Update state
        state["validation_completed"] = True
        state["validation_result"] = validation_result
        
        # Set exit code for main script
        if not validation_result["should_continue"]:
            state["exit_code"] = validation_result["exit_code"]
            state["critical_failure"] = True
        
        return state