# tool_manager.py

import logging
import asyncio
import functools
import os
import json
import aiohttp
import aiosqlite
import subprocess
import concurrent.futures
from typing import Any, Dict, List, Optional
import cv2
from bs4 import BeautifulSoup
try:
    from image_generator import generate_image  # 画像生成関数を実装済みのモジュールからimport
except ImportError:
    # 画像生成機能が利用できない場合のフォールバック
    def generate_image(prompt: str, **kwargs) -> str:
        return f"エラー: 画像生成機能が利用できません。プロンプト: {prompt}"


def log_tool(func):
    """Simple decorator to log tool invocation."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logging.info("tool start: %s", func.__name__)
        result = await func(*args, **kwargs)
        logging.info("tool end: %s", func.__name__)
        return result

    return wrapper


class ToolManager:
    def __init__(self, db_path: str = "agent_state.db", root_dir: Optional[str] = None):
        self.db_path = db_path
        self.root_dir = root_dir
        self.db_connection = None
        self.tools = {
            "respond_to_user": self.respond_to_user,
            "generate_image": self.generate_image,
            "simple_math": self.simple_math,
            "get_current_time": self.get_current_time,
        }
        self.shell_sessions: Dict[str, asyncio.subprocess.Process] = {}
        self._agent = None  # 必要に応じてセット

    def get_tool_by_name(self, name: str):
        return self.tools.get(name)

    async def __aenter__(self):
        await self._get_db_connection()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.db_connection:
            await self.db_connection.close()
            self.db_connection = None

    async def _get_db_connection(self):
        if self.db_connection is None:
            self.db_connection = await aiosqlite.connect(self.db_path)
            await self._initialize_db()
        return self.db_connection

    async def _initialize_db(self):
        conn = await self._get_db_connection()
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                role TEXT,
                content TEXT
            )"""
        )
        await conn.commit()

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
        ]

    # ------------------------------------------------------------------
    # Agent management (placeholders)
    # ------------------------------------------------------------------
    async def agent_update_plan(self, agent_id: str, plan: str) -> Dict[str, Any]:
        return {"status": "updated", "agent": agent_id}

    async def agent_advance_phase(self, agent_id: str) -> Dict[str, Any]:
        return {"phase": 1}

    async def agent_end_task(self, agent_id: str) -> Dict[str, Any]:
        return {"status": "completed"}

    async def agent_schedule_task(self, agent_id: str, schedule: str) -> Dict[str, Any]:
        return {"schedule": schedule}

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------
    async def message_notify_user(self, user: str, message: str) -> Dict[str, Any]:
        logging.info("notify %s: %s", user, message)
        return {"message": message}

    async def message_ask_user(self, user: str, question: str) -> Dict[str, Any]:
        logging.info("ask %s: %s", user, question)
        return {"status": "awaiting"}

    # ------------------------------------------------------------------
    # Shell commands
    # ------------------------------------------------------------------
    async def shell_exec(self, command: str, session_id: str) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.shell_sessions[session_id] = proc
        return {"status": "running"}

    async def shell_wait(self, session_id: str) -> Dict[str, Any]:
        proc = self.shell_sessions.get(session_id)
        if not proc:
            logging.error("shell_wait: missing session %s", session_id)
            return {"error": "session not found"}
        stdout, stderr = await proc.communicate()
        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
        }

    async def shell_kill(self, session_id: str) -> Dict[str, Any]:
        proc = self.shell_sessions.pop(session_id, None)
        if not proc:
            return {"error": "session not found"}
        proc.kill()
        await proc.wait()
        return {"status": "killed"}

    async def shell_view(self, session_id: str) -> Dict[str, Any]:
        proc = self.shell_sessions.get(session_id)
        if not proc:
            return {"error": "session not found"}
        return {"pid": proc.pid}

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def _safe_path(self, path: str) -> Optional[str]:
        abs_path = os.path.abspath(path)
        if self.root_dir is not None:
            if not abs_path.startswith(os.path.abspath(self.root_dir)):
                return None
        return abs_path

    async def file_read(self, abs_path: str) -> Dict[str, Any]:
        path = self._safe_path(abs_path)
        if not path or not os.path.exists(path):
            return {"error": "file not found"}
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            content = await loop.run_in_executor(pool, lambda: open(path, "r", encoding="utf-8").read())
        return {"content": content}

    async def file_append_text(self, abs_path: str, text: str) -> Dict[str, Any]:
        path = self._safe_path(abs_path)
        if not path:
            return {"error": "invalid path"}
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, lambda: open(path, "a", encoding="utf-8").write(text))
        return {"status": "appended"}

    async def file_replace_text(self, abs_path: str, old: str, new: str) -> Dict[str, Any]:
        path = self._safe_path(abs_path)
        if not path or not os.path.exists(path):
            return {"error": "file not found"}
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            def _replace():
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()
                data = data.replace(old, new)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
            await loop.run_in_executor(pool, _replace)
        return {"status": "replaced"}

    # ------------------------------------------------------------------
    # Media operations (simplified)
    # ------------------------------------------------------------------
    async def media_generate_image(self, prompt: str, out_path: str) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, generate_image, prompt, {"out_path": out_path})
        return {"path": out_path}

    async def media_generate_speech(self, text: str, out_path: str) -> Dict[str, Any]:
        return {"error": "TTS not configured"}

    async def media_analyze_image(self, path: str) -> Dict[str, Any]:
        try:
            import pytesseract
            from PIL import Image
        except Exception:
            return {"error": "pytesseract not available"}
        text = pytesseract.image_to_string(Image.open(path))
        return {"text": text}

    async def media_recognize_speech(self, path: str) -> Dict[str, Any]:
        try:
            import speech_recognition as sr
        except Exception:
            return {"error": "speech_recognition not available"}
        r = sr.Recognizer()
        with sr.AudioFile(path) as source:
            audio = r.record(source)
        text = r.recognize_sphinx(audio)
        return {"text": text}

    async def media_analyze_video(self, path: str) -> Dict[str, Any]:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"error": "cannot open"}
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 1
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return {"frames": frames, "duration": frames / fps, "width": width, "height": height}

    async def media_describe_video(self, path: str) -> Dict[str, Any]:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"error": "cannot open"}
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return {"error": "no frame"}
        avg_color = frame.mean(axis=None).tolist()
        return {"avg_color": avg_color}

    # ------------------------------------------------------------------
    # Information search
    # ------------------------------------------------------------------
    async def info_search_web(self, query: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://duckduckgo.com/html/", params={"q": query}) as resp:
                html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for a in soup.select("a.result__a"):
            results.append({"title": a.text, "url": a.get("href")})
        return {"results": results}

    async def info_search_api(self, url: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
        return data

    async def info_search_image(self, query: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.unsplash.com/search/photos", params={"query": query}) as resp:
                data = await resp.json()
        results = []
        for r in data.get("results", []):
            results.append({"id": r.get("id"), "url": r.get("urls", {}).get("small"), "alt": r.get("alt_description")})
        return {"results": results}

    # ------------------------------------------------------------------
    # Browser and service placeholders
    # ------------------------------------------------------------------
    async def browser_navigate(self, url: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_view(self) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_click(self, selector: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_input(self, selector: str, text: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_press_key(self, key: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_select_option(self, selector: str, value: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_save_image(self, path: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_scroll_up(self) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_scroll_down(self) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_console_exec(self, command: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def browser_console_view(self) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def service_expose_port(self, port: int) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def service_deploy_frontend(self, repo: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    async def service_deploy_backend(self, repo: str) -> Dict[str, Any]:
        return {"error": "not implemented"}

    # ------------------------------------------------------------------
    # Slide utilities
    # ------------------------------------------------------------------
    async def slide_initialize(self, project_dir: str) -> Dict[str, Any]:
        os.makedirs(project_dir, exist_ok=True)
        return {"project": project_dir}

    async def slide_present(self, project_dir: str) -> Dict[str, Any]:
        return {"status": "presenting"}
