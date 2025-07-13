from typing import Any, Dict, List

from state_manager import StateManager


class GoalManager:
    """Derive potential goals from history and a user profile."""

    def __init__(self, state_manager: StateManager, user_profile: Dict[str, Any]):
        self.state_manager = state_manager
        self.user_profile = user_profile
        self._confirmed: List[str] = []

    async def derive_goals(self) -> List[str]:
        """Suggest goals based on past user messages and interests."""
        data = await self.state_manager.load()
        history = " ".join(
            msg.get("content", "")
            for msg in data.get("history", [])
            if msg.get("role") == "user"
        )
        suggestions: List[str] = []
        hist_lower = history.lower()
        for interest in self.user_profile.get("interests", []):
            if interest.lower() in hist_lower:
                suggestions.append(f"Learn more about {interest}")
        if not suggestions and history:
            suggestions.append(f"Follow up on: {history.strip()}")
        return suggestions

    async def confirm_goals(self, goals: List[str]) -> None:
        self._confirmed = goals

    async def current_goals(self) -> List[str]:
        return self._confirmed
