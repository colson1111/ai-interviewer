"""Agent registry for managing available agents."""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from ..core import AgentCapability, AgentMessage, InterviewContext
from .base import BaseInterviewAgent


@dataclass
class AgentRegistration:
    """Information about a registered agent."""

    agent: BaseInterviewAgent
    registered_at: float
    priority: int = 0  # Higher priority agents are preferred
    tags: Set[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = set()


class AgentRegistry:
    """Registry for managing and discovering interview agents."""

    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._capability_index: Dict[AgentCapability, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}

    def register_agent(
        self,
        agent: BaseInterviewAgent,
        priority: int = 0,
        tags: Optional[Set[str]] = None,
    ):
        """
        Register an agent with the registry.

        Args:
            agent: The agent to register
            priority: Priority level (higher = preferred)
            tags: Optional tags for categorization
        """
        if tags is None:
            tags = set()

        registration = AgentRegistration(
            agent=agent, registered_at=time.time(), priority=priority, tags=tags
        )

        self._agents[agent.name] = registration

        # Update capability index
        for capability in agent.get_capabilities():
            if capability not in self._capability_index:
                self._capability_index[capability] = set()
            self._capability_index[capability].add(agent.name)

        # Update tag index
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(agent.name)

        print(
            f"Registered agent: {agent.name} with capabilities: {[c.value for c in agent.get_capabilities()]}"
        )

    def unregister_agent(self, agent_name: str):
        """Remove an agent from the registry."""
        if agent_name not in self._agents:
            return

        registration = self._agents[agent_name]
        agent = registration.agent

        # Remove from capability index
        for capability in agent.get_capabilities():
            if capability in self._capability_index:
                self._capability_index[capability].discard(agent_name)
                if not self._capability_index[capability]:
                    del self._capability_index[capability]

        # Remove from tag index
        for tag in registration.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(agent_name)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        del self._agents[agent_name]
        print(f"Unregistered agent: {agent_name}")

    def get_agent(self, agent_name: str) -> Optional[BaseInterviewAgent]:
        """Get a specific agent by name."""
        registration = self._agents.get(agent_name)
        return registration.agent if registration else None

    def get_all_agents(self) -> List[BaseInterviewAgent]:
        """Get all registered agents."""
        return [reg.agent for reg in self._agents.values() if reg.agent.is_enabled]

    def get_agents_by_capability(self, capability: AgentCapability) -> List[str]:
        """Get agent names that have a specific capability."""
        agent_names = self._capability_index.get(capability, set())
        # Return only enabled agents, sorted by priority
        enabled_agents = []
        for name in agent_names:
            registration = self._agents.get(name)
            if registration and registration.agent.is_enabled:
                enabled_agents.append((name, registration.priority))

        # Sort by priority (descending) then by name
        enabled_agents.sort(key=lambda x: (-x[1], x[0]))
        return [name for name, _ in enabled_agents]

    def get_agents_by_tag(self, tag: str) -> List[str]:
        """Get agent names with a specific tag."""
        agent_names = self._tag_index.get(tag, set())
        return [
            name
            for name in agent_names
            if name in self._agents and self._agents[name].agent.is_enabled
        ]

    def find_best_agents(
        self, message: AgentMessage, context: InterviewContext, max_agents: int = 3
    ) -> List[tuple[str, float]]:
        """
        Find the best agents to handle a message.

        Args:
            message: The message to handle
            context: Current interview context
            max_agents: Maximum number of agents to return

        Returns:
            List of (agent_name, confidence_score) tuples, sorted by confidence
        """
        agent_scores = []

        for registration in self._agents.values():
            agent = registration.agent
            if not agent.is_enabled:
                continue

            try:
                confidence = agent.can_handle(message, context)
                if confidence > 0:
                    # Boost score based on priority
                    adjusted_score = confidence + (registration.priority * 0.1)
                    adjusted_score = min(1.0, adjusted_score)  # Cap at 1.0
                    agent_scores.append((agent.name, adjusted_score))
            except Exception as e:
                print(f"Error evaluating agent {agent.name}: {e}")
                continue

        # Sort by confidence score (descending)
        agent_scores.sort(key=lambda x: x[1], reverse=True)

        return agent_scores[:max_agents]

    def get_capabilities_summary(self) -> Dict[str, List[str]]:
        """Get a summary of all capabilities and which agents provide them."""
        summary = {}
        for capability, agent_names in self._capability_index.items():
            enabled_agents = [
                name
                for name in agent_names
                if name in self._agents and self._agents[name].agent.is_enabled
            ]
            if enabled_agents:
                summary[capability.value] = enabled_agents
        return summary

    def get_registry_status(self) -> Dict[str, Any]:
        """Get overall registry status."""
        total_agents = len(self._agents)
        enabled_agents = len(
            [reg for reg in self._agents.values() if reg.agent.is_enabled]
        )

        return {
            "total_agents": total_agents,
            "enabled_agents": enabled_agents,
            "total_capabilities": len(self._capability_index),
            "agents": {
                name: reg.agent.get_status() for name, reg in self._agents.items()
            },
            "capabilities": self.get_capabilities_summary(),
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all agents."""
        results = {"healthy_agents": [], "unhealthy_agents": [], "total_checked": 0}

        for name, registration in self._agents.items():
            results["total_checked"] += 1
            agent = registration.agent

            try:
                # Basic health check - agent should be able to report status
                status = agent.get_status()
                if agent.is_enabled and status:
                    results["healthy_agents"].append(name)
                else:
                    results["unhealthy_agents"].append(name)
            except Exception as e:
                results["unhealthy_agents"].append(name)
                print(f"Health check failed for agent {name}: {e}")

        return results
