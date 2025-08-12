from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timezone


class AgentState(TypedDict, total=False):
    orchestrator: Any
    config_path: str
    user_story: str
    logger: Any

    # Workflow artifacts
    framework_details: Dict[str, Any]
    framework_initialized: bool
    feature_path: str
    step_definitions_path: str

    # Execution
    test_passed: bool
    test_executed: bool
    test_exec_result: str
    scenario_results: List[Dict[str, Any]]

    # Healing
    needs_self_heal: bool
    healing_attempts: int
    healing_types: List[str]
    syntax_healed: bool
    runtime_healed: bool

    # Diagnostics
    diagnosed: bool
    error_type: Optional[str]
    error_details: Optional[str]
    error_specifics: Dict[str, Any]

    # Control
    manual_review: bool
    validation_completed: bool
    report_path: str

    # Book-keeping
    current_step: str
    execution_trail: List[Dict[str, Any]]
    max_healing_attempts: int
    enable_auto_healing: bool