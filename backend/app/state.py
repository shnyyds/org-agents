from typing import List, Dict, Any, TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict, total=False):
    """
    State for the Elevator Multi-Agent system.
    """
    # History of messages for the session
    messages: Annotated[List[BaseMessage], operator.add]

    # Context for streaming and session info (not merged, just replaced)
    # Also stores internal tracking like _clarification_count, _clarification_remaining
    context: Dict[str, Any]

    # Current department handling the task
    current_department: str

    # Current target agent within a department
    active_agent: str

    # Execution history for the current request
    execution_log: Annotated[List[Dict[str, Any]], operator.add]

    # Task analysis from CEO
    intent_analysis: Dict[str, Any]

    # Sequential Plan: List of departments to visit
    plan: List[str]

    # Current step index in the plan
    plan_step: int

    # Sub-Plan: List of sub-agents to visit within a department
    sub_plan: List[str]

    # Current step index in the sub-plan
    sub_plan_step: int

    # Results from various departments
    results: Annotated[Dict[str, Any], operator.ior]

    # Tech Department Pipeline Data
    prd: str
    code: str
    test_report: Dict[str, Any]
    deployment_report: str

    # Control flags
    requires_human_approval: bool
    is_task_complete: bool
    next_step: str
    test_passed: bool

    # --- Week 1: Task lifecycle & requirement tracking ---

    # Task phase tracking
    # Values: idle | requirement_analysis | requirement_clarification |
    #         sub_plan_generation | dispatch_execution | test_reflow |
    #         ops_finish | completed
    task_phase: str

    # Requirement confirmation status
    # Values: pending | clear | unclear | confirmed
    requirement_confirmation_status: str

    # Requirement versioning
    original_requirement: str    # Raw user query, set once
    latest_supplement: str       # Most recent user clarification
    confirmed_requirement: str   # Final confirmed requirement for execution

    # Current executor tracking
    current_executor: str        # Sub-agent ID actively running

    # Unified sub-task results: {"product": {...}, "developer": {...}, ...}
    sub_task_results: Annotated[Dict[str, Any], operator.ior]

    # Reflow control
    reflow_count: int            # Times tester->developer reflow has happened
    max_reflow: int              # Cap to prevent infinite loops (default 2)

    # User modification feedback (injected during "modify" confirmation action)
    user_modification_feedback: str
