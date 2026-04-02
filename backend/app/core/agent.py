from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.state import AgentState

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    """
    def __init__(self, name: str, department: str):
        self.name = name
        self.department = department

    @abstractmethod
    async def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Runs the agent logic based on the current state.
        Returns the updated state dictionary.
        """
        pass

class DepartmentLead(BaseAgent):
    """
    Base class for department lead agents.
    """
    def __init__(self, name: str, department: str):
        super().__init__(name, department)
        self.sub_agents = []

    def add_sub_agent(self, agent: BaseAgent):
        self.sub_agents.append(agent)

    @abstractmethod
    async def orchestrate(self, state: AgentState) -> Dict[str, Any]:
        """
        Orchestrates internal sub-agents.
        """
        pass
