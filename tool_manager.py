# tool_manager.py

import logging
import asyncio
from typing import Any, Dict, List
try:
    from image_generator import generate_image  # 画像生成関数を実装済みのモジュールからimport
except ImportError:
    # 画像生成機能が利用できない場合のフォールバック
    def generate_image(prompt: str, **kwargs) -> str:
        return f"エラー: 画像生成機能が利用できません。プロンプト: {prompt}"

class ToolManager:
    def __init__(self):
        self.tools = {
            "respond_to_user": self.respond_to_user,
            "generate_image": self.generate_image,
            "simple_math": self.simple_math,
            "get_current_time": self.get_current_time,
            "capture_screenshot": self.capture_screenshot,
        }
        self._agent = None  # 必要に応じてセット

    def get_tool_by_name(self, name: str):
        return self.tools.get(name)

    async def respond_to_user(self, text: str) -> str:
        return text

    async def generate_image(self, prompt: str, **kwargs) -> str:
        """
        画像生成用ツール関数。追加の引数（num_inference_steps 等）は **kwargs で吸収。
        """
        if not self._agent:
            logging.warning("VRAM管理エージェントがセットされていません。画像生成は直接関数を呼びます。")
            loop = asyncio.get_running_loop()
            try:
                file_path = await loop.run_in_executor(None, generate_image, prompt, kwargs)
                return file_path
            except Exception as e:
                logging.error(f"画像生成中のエラー: {e}", exc_info=True)
                return f"エラー: 画像の生成に失敗しました - {e}"

        try:
            logging.info("画像生成のため、LLMをVRAMからアンロードします...")
            await self._agent.unload_agents()

            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, generate_image, prompt, kwargs)
            return file_path
        except Exception as e:
            logging.error(f"画像生成中のエラー: {e}", exc_info=True)
            return f"エラー: 画像の生成に失敗しました - {e}"

    async def simple_math(self, expression: str) -> str:
        try:
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

    async def capture_screenshot(self, output_path: str | None = None) -> str:
        """Capture a screenshot of the current screen and save to a file."""
        try:
            import os
            import tempfile
            import pyautogui

            if output_path is None:
                fd, path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                output_path = path

            loop = asyncio.get_running_loop()

            def _capture(path: str) -> None:
                img = pyautogui.screenshot()
                img.save(path)

            await loop.run_in_executor(None, _capture, output_path)
            return output_path
        except Exception as e:
            logging.error(f"capture_screenshot error: {e}")
            return f"エラー: スクリーンショットの取得に失敗しました - {e}"

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
                            "prompt": {"type": "string"},
                            "width": {"type": "integer", "default": 512},
                            "height": {"type": "integer", "default": 512},
                            "num_inference_steps": {"type": "integer", "default": 30},
                            "guidance_scale": {"type": "number", "default": 7.5},
                            "seed": {"type": "integer"}
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
            {
                "type": "function",
                "function": {
                    "name": "capture_screenshot",
                    "description": "現在の画面をキャプチャして画像ファイルとして保存します。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                },
            },
        ]
