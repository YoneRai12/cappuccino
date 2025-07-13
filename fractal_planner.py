from typing import Any, Dict, List, Optional

from config import settings
from planner import Planner as BasicPlanner


class FractalPlanner:
    """Recursive planner breaking tasks into hierarchical substeps."""

    def __init__(
        self,
        depth: int | None = None,
        breadth: int | None = None,
        base_planner: Optional[BasicPlanner] = None,
    ) -> None:
        self.depth = depth if depth is not None else settings.fractal_depth
        self.breadth = breadth if breadth is not None else settings.fractal_breadth
        self.base_planner = base_planner or BasicPlanner()

    def _search(self, context: str, depth: int) -> List[Dict[str, Any]]:
        steps = self.base_planner.create_plan(context)[: self.breadth]
        if depth <= 1:
            return steps
        for step in steps:
            step["substeps"] = self._search(step["action"], depth - 1)
        return steps

    def create_plan(self, context: str) -> List[Dict[str, Any]]:
        """Generate a hierarchical plan using recursive expansion."""
        return self._search(context, self.depth)
