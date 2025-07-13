import asyncio
from typing import Optional

from cappuccino_agent import CappuccinoAgent
from tool_manager import ToolManager
from config import settings


async def chat_once(agent: CappuccinoAgent, message: str) -> str:
    """Send a single message to the agent and return its response."""
    try:
        result = await agent.run(message)
    except Exception as exc:  # pragma: no cover - defensive
        return f"error: {exc}"
    return result if isinstance(result, str) else str(result)


async def chat_loop(api_key: Optional[str] = None) -> None:
    """Interactive CLI chat loop with the Cappuccino agent."""
    agent = CappuccinoAgent(api_key=api_key or settings.openai_api_key,
                           tool_manager=ToolManager(db_path=":memory:"))
    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() in {"exit", "quit"}:
                break
            response = await chat_once(agent, user_input)
            print(f"Cappuccino: {response}")
    finally:
        await agent.close()


if __name__ == "__main__":  # pragma: no cover - manual run
    asyncio.run(chat_loop())
