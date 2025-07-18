# tool_manager.py (VRAM管理の門番・最終版)
import logging
import asyncio
from typing import Any, Dict, List, Optional
from image_generator import generate_image

class ToolManager:
    def __init__(self):
        self._agent: Optional[Any] = None

    def set_agent(self, agent: Any):
        self._agent = agent

    async def get_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "テキストプロンプトに基づいて画像を生成します。",
                    "parameters": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "respond_to_user",
                    "description": "挨拶や単純な応答など、ユーザーに直接テキストで返信します。",
                    "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
                },
            }
        ]
    
    async def respond_to_user(self, text: str) -> str:
        return text

    async def generate_image(self, prompt: str) -> str:
        if not self._agent:
            return "エラー: VRAM管理の初期化に失敗しました。"
        try:
            logging.info("画像生成のため、LLMをVRAMからアンロードします...")
            await self._agent.unload_agents()
            
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, generate_image, prompt)
            
            return f"画像を生成しました。パス: {file_path}"
        except Exception as e:
            logging.error(f"画像生成中のエラー: {e}", exc_info=True)
            return f"エラー: 画像の生成に失敗しました - {e}"