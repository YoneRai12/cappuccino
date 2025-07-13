import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from planner import Planner
from fractal_planner import FractalPlanner


def test_fractal_planner_nested():
    planner = FractalPlanner(depth=2, breadth=2)
    plan = planner.create_plan("collect data. analyze results")
    assert len(plan) == 2
    assert "substeps" in plan[0]
    assert isinstance(plan[0]["substeps"], list)


def test_planner_modes_basic_vs_fractal():
    ctx = "step one. step two"
    basic = Planner()
    fractal = Planner(mode="fractal", fractal_depth=2, fractal_breadth=2)
    basic_plan = basic.create_plan(ctx)
    fractal_plan = fractal.create_plan(ctx)
    assert len(basic_plan) == 2
    assert len(fractal_plan) == 2
    assert "substeps" in fractal_plan[0]
