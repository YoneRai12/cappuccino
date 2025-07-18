# tool_manager.py
import logging
import asyncio
from typing import Any, Dict, List
from image_generator import generate_image  # 画像生成関数を実装済みのモジュールからimport

class ToolManager:
    def __init__(self):
        self.tools = {
            "respond_to_user": self.respond_to_user,
            "generate_image": self.generate_image,
            "simple_math": self.simple_math,
            "get_current_time": self.get_current_time,
        }
        self._agent = None  # 必要に応じてセット

    def get_tool_by_name(self, name: str):
        return self.tools.get(name)

    async def respond_to_user(self, text: str) -> str:
        return text

    async def generate_image(self, prompt: str) -> str:
        if not self._agent:
            logging.warning("VRAM管理エージェントがセットされていません。画像生成は直接関数を呼びます。")
            loop = asyncio.get_running_loop()
            try:
                file_path = await loop.run_in_executor(None, generate_image, prompt)
                return f"[画像生成成功] 画像を生成しました。パス: {file_path}"
            except Exception as e:
                logging.error(f"画像生成中のエラー: {e}", exc_info=True)
                return f"エラー: 画像の生成に失敗しました - {e}"

        try:
            logging.info("画像生成のため、LLMをVRAMからアンロードします...")
            await self._agent.unload_agents()

            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, generate_image, prompt)

            return f"[画像生成成功] 画像を生成しました。パス: {file_path}"
        except Exception as e:
            logging.error(f"画像生成中のエラー: {e}", exc_info=True)
            return f"エラー: 画像の生成に失敗しました - {e}"

    async def simple_math(self, expression: str) -> str:
        """簡単な計算式を計算して返す。例: '3 + 5'"""
        try:
            # 危険なのでevalは使わず、簡単な計算のみ許可
            allowed_chars = "0123456789+-*/(). "
            if any(c not in allowed_chars for c in expression):
                return "エラー: 許可されていない文字が含まれています。"
            result = eval(expression)
            return f"計算結果: {result}"
        except Exception as e:
            return f"計算エラー: {e}"

    async def get_current_time(self) -> str:
        import datetime
        now = datetime.datetime.now()
        return f"現在の日時は {now.strftime('%Y-%m-%d %H:%M:%S')} です。"

    async def get_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "テキストプロンプトに基づいて画像を生成します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"}
                        },
                        "required": ["prompt"]
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "respond_to_user",
                    "description": "ユーザーにテキストで返信します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "simple_math",
                    "description": "簡単な計算を行います。例: '3 + 5'。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"}
                        },
                        "required": ["expression"]
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "現在の日時を返します。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                },
            },
        ]
