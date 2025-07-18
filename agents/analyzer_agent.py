# agents/analyzer_agent.py (最終・確定版)
import asyncio
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent

class AnalyzerAgent(BaseAgent):
    async def analyze(self, result_queue: asyncio.Queue) -> List[Dict[str, Any]]:
        results = []
        while not result_queue.empty():
            results.append(await result_queue.get()); result_queue.task_done()
        logging.info(f"分析する結果: {results}")
        if not results: return [{"result": "タスクは実行されましたが、結果はありませんでした。"}]
        final_response = "\n".join([str(r.get("result", "")) for r in results])
        return [{"result": final_response}]