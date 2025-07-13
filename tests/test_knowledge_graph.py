import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import pytest

from tool_manager import ToolManager


@pytest.mark.asyncio
async def test_graph_persistence(tmp_path):
    db = tmp_path / "graph.db"
    async with ToolManager(db_path=str(db)) as tm:
        await tm.graph_add_entity("Alice")
        await tm.graph_add_entity("Bob")
        await tm.graph_add_relation("Alice", "Bob", "knows")
        result = await tm.graph_query("Alice")
        assert ("knows", "Bob") in result["relations"]

    async with ToolManager(db_path=str(db)) as tm2:
        result = await tm2.graph_query("Alice")
        assert ("knows", "Bob") in result["relations"]


@pytest.mark.asyncio
async def test_graph_remove_relation(tmp_path):
    db = tmp_path / "graph.db"
    async with ToolManager(db_path=str(db)) as tm:
        await tm.graph_add_entity("A")
        await tm.graph_add_entity("B")
        await tm.graph_add_relation("A", "B", "likes")
        await tm.graph_remove_relation("A", "B", "likes")
        result = await tm.graph_query("A")
        assert ("likes", "B") not in result["relations"]
