from typing import Any, Dict, List

from config import settings


class Planner:
    """Generate plans from user context using selectable strategy."""

    def __init__(
        self,
        mode: str = "basic",
        *,
        fractal_depth: int | None = None,
        fractal_breadth: int | None = None,
    ) -> None:
        self.mode = mode
        if self.mode == "fractal":
            from fractal_planner import FractalPlanner

            self._planner = FractalPlanner(
                depth=fractal_depth or settings.fractal_depth,
                breadth=fractal_breadth or settings.fractal_breadth,
            )
        else:
            self._planner = None

    def _basic_plan(self, context: str) -> List[Dict[str, Any]]:
        steps = []
        for idx, part in enumerate(context.split(".")):
            item = part.strip()
            if item:
                steps.append({"step": idx + 1, "action": item})
        if not steps:
            steps.append({"step": 1, "action": context.strip()})
        return steps

    def create_plan(self, context: str) -> List[Dict[str, Any]]:
        """Create a plan based on the configured mode."""
        if self.mode == "fractal" and self._planner is not None:
            return self._planner.create_plan(context)
        return self._basic_plan(context)
