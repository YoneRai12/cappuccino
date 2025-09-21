"""Utility class providing asynchronous tool operations for the Cappuccino agent."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import aiosqlite
import importlib
import importlib.util
import openai
import subprocess

from knowledge_graph import KnowledgeGraph

LOGGER = logging.getLogger(__name__)


def _import_optional(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.find_spec(name)
    if spec is None:
        return None
    return importlib.import_module(name)


def log_tool(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        LOGGER.info("Tool '%s' invoked", func.__name__)
        return await func(*args, **kwargs)

    return wrapper


class ToolManager:
    """Manage miscellaneous tools that the agents rely on during execution.

    The implementation favours predictability and graceful degradation so that
    the unit tests can run in an isolated environment without external
    services.
    """

    def __init__(self, db_path: str = ":memory:", root_dir: Optional[str] = None) -> None:
        self.db_path = db_path
        self.root_dir = Path(root_dir).expanduser().resolve() if root_dir else None
        self.db_connection: Optional[aiosqlite.Connection] = None
        self._shell_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._shell_tasks: Dict[str, asyncio.Task[tuple[bytes, bytes]]] = {}
        self._shell_results: Dict[str, Dict[str, Any]] = {}
        self._graph: Optional[KnowledgeGraph] = None
        self.tools = {
            "respond_to_user": self.respond_to_user,
            "generate_image": self.generate_image,
            "simple_math": self.simple_math,
            "get_current_time": self.get_current_time,
            "file_read": self.file_read,
            "file_append_text": self.file_append_text,
            "file_replace_text": self.file_replace_text,
            "shell_exec": self.shell_exec,
            "shell_wait": self.shell_wait,
            "shell_kill": self.shell_kill,
            "shell_view": self.shell_view,
            "media_generate_image": self.media_generate_image,
            "media_generate_speech": self.media_generate_speech,
            "media_analyze_image": self.media_analyze_image,
            "media_recognize_speech": self.media_recognize_speech,
            "media_analyze_video": self.media_analyze_video,
            "media_describe_video": self.media_describe_video,
            "info_search_web": self.info_search_web,
            "info_search_api": self.info_search_api,
            "info_search_image": self.info_search_image,
            "slide_initialize": self.slide_initialize,
            "slide_present": self.slide_present,
        }

    async def __aenter__(self) -> "ToolManager":
        await self._ensure_db()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        await self.close()

    async def close(self) -> None:
        if self.db_connection is not None:
            await self.db_connection.close()
            self.db_connection = None
        self._graph = None

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self.db_connection is None:
            self.db_connection = await aiosqlite.connect(self.db_path)
            await self.db_connection.execute("PRAGMA journal_mode=WAL")
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT
                )
                """
            )
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    agent_id TEXT PRIMARY KEY,
                    plan TEXT,
                    phase INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    schedule TEXT
                )
                """
            )
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
                """
            )
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tools (
                    name TEXT PRIMARY KEY,
                    code TEXT
                )
                """
            )
            await self.db_connection.commit()
        return self.db_connection

    async def _get_db_connection(self) -> aiosqlite.Connection:
        return await self._ensure_db()

    async def _load_graph(self) -> KnowledgeGraph:
        if self._graph is not None:
            return self._graph
        conn = await self._ensure_db()
        async with conn.execute("SELECT data FROM knowledge_graph WHERE id=1") as cursor:
            row = await cursor.fetchone()
        if row and row[0]:
            self._graph = KnowledgeGraph.from_json(row[0])
        else:
            self._graph = KnowledgeGraph()
        return self._graph

    async def _save_graph(self, graph: KnowledgeGraph) -> None:
        conn = await self._ensure_db()
        await conn.execute(
            "INSERT INTO knowledge_graph(id, data) VALUES(1, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
            (graph.to_json(),),
        )
        await conn.commit()
        self._graph = graph

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _resolve_path(self, raw_path: str) -> Optional[Path]:
        try:
            candidate = Path(raw_path).expanduser()
            resolved = candidate.resolve()
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("Failed to resolve path %s: %s", raw_path, exc)
            return None

        if self.root_dir:
            try:
                resolved.relative_to(self.root_dir)
            except ValueError:
                LOGGER.warning("Attempt to access path outside root: %s", resolved)
                return None
        return resolved

    @staticmethod
    def _session_get(session: Any, url: str, **kwargs: Any):
        try:
            return session.get(url, **kwargs)
        except TypeError:
            return session.get(url)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------
    async def set_cached_result(self, key: str, value: Any) -> None:
        conn = await self._ensure_db()
        payload = json.dumps(value)
        await conn.execute(
            """
            INSERT INTO cache(cache_key, cache_value)
            VALUES(?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET cache_value=excluded.cache_value
            """,
            (key, payload),
        )
        await conn.commit()

    async def get_cached_result(self, key: str) -> Any:
        conn = await self._ensure_db()
        async with conn.execute("SELECT cache_value FROM cache WHERE cache_key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return row[0]

    # ------------------------------------------------------------------
    # Agent task management helpers
    # ------------------------------------------------------------------
    async def agent_update_plan(self, agent_id: str, plan: str) -> Dict[str, Any]:
        conn = await self._ensure_db()
        await conn.execute(
            """
            INSERT INTO agent_tasks(agent_id, plan, phase, status)
            VALUES(?, ?, 0, 'pending')
            ON CONFLICT(agent_id) DO UPDATE SET plan=excluded.plan
            """,
            (agent_id, plan),
        )
        await conn.commit()
        return {"agent_id": agent_id, "plan": plan}

    async def _ensure_agent_task_row(
        self, conn: aiosqlite.Connection, agent_id: str
    ) -> None:
        await conn.execute(
            """
            INSERT INTO agent_tasks(agent_id, plan, phase, status, schedule)
            VALUES(?, '', 0, 'pending', NULL)
            ON CONFLICT(agent_id) DO NOTHING
            """,
            (agent_id,),
        )

    async def agent_advance_phase(self, agent_id: str) -> Dict[str, Any]:
        conn = await self._ensure_db()
        await self._ensure_agent_task_row(conn, agent_id)
        await conn.execute(
            "UPDATE agent_tasks SET phase = phase + 1 WHERE agent_id = ?",
            (agent_id,),
        )
        async with conn.execute(
            "SELECT phase FROM agent_tasks WHERE agent_id = ?", (agent_id,)
        ) as cursor:
            row = await cursor.fetchone()
        await conn.commit()
        phase = row[0] if row else 0
        return {"agent_id": agent_id, "phase": phase}

    async def agent_end_task(self, agent_id: str) -> Dict[str, Any]:
        conn = await self._ensure_db()
        await self._ensure_agent_task_row(conn, agent_id)
        await conn.execute(
            "UPDATE agent_tasks SET status = 'completed' WHERE agent_id = ?",
            (agent_id,),
        )
        await conn.commit()
        return {"agent_id": agent_id, "status": "completed"}

    async def agent_schedule_task(self, agent_id: str, schedule: str) -> Dict[str, Any]:
        conn = await self._ensure_db()
        await self._ensure_agent_task_row(conn, agent_id)
        await conn.execute(
            "UPDATE agent_tasks SET schedule = ? WHERE agent_id = ?",
            (schedule, agent_id),
        )
        await conn.commit()
        return {"agent_id": agent_id, "schedule": schedule}

    # ------------------------------------------------------------------
    # Knowledge graph helpers
    # ------------------------------------------------------------------
    async def graph_add_entity(self, name: str, **attrs: Any) -> Dict[str, Any]:
        graph = await self._load_graph()
        graph.add_entity(name, **attrs)
        await self._save_graph(graph)
        return {"entity": name}

    async def graph_add_relation(self, source: str, target: str, relation: str, **attrs: Any) -> Dict[str, Any]:
        graph = await self._load_graph()
        graph.add_relation(source, target, relation, **attrs)
        await self._save_graph(graph)
        return {"relation": relation, "source": source, "target": target}

    async def graph_remove_relation(self, source: str, target: str, relation: str) -> Dict[str, Any]:
        graph = await self._load_graph()
        graph.remove_relation(source, target, relation)
        await self._save_graph(graph)
        return {"removed": (source, target, relation)}

    async def graph_query(self, entity: str) -> Dict[str, Any]:
        graph = await self._load_graph()
        relations = graph.query(entity)
        return {"entity": entity, "relations": relations}

    # ------------------------------------------------------------------
    # Tool generation helpers
    # ------------------------------------------------------------------
    async def generate_tool_from_failure(
        self, task_description: str, error_message: str, api_key: Optional[str]
    ) -> Dict[str, Any]:
        client = openai.AsyncOpenAI(api_key=api_key)
        prompt = (
            "You are a Python assistant that writes small async utility functions.\n"
            f"Task description: {task_description}\n"
            f"Observed error: {error_message}\n"
            "Write a single async function that resolves the issue."
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return only valid Python code."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        code = response.choices[0].message.content
        namespace: Dict[str, Any] = {}
        exec(code, namespace)
        func = next(value for value in namespace.values() if callable(value))
        setattr(self, func.__name__, func)
        self.tools[func.__name__] = func

        conn = await self._ensure_db()
        await conn.execute(
            "INSERT INTO tools(name, code) VALUES(?, ?) ON CONFLICT(name) DO UPDATE SET code=excluded.code",
            (func.__name__, code),
        )
        await conn.commit()
        try:
            subprocess.run(["python", "-m", "compileall", "-"], input=code.encode(), check=False)
        except Exception:  # pragma: no cover - optional best effort
            pass
        return {"name": func.__name__, "code": code}

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------
    async def message_notify_user(self, user_id: str, message: str) -> Dict[str, Any]:
        return {"user_id": user_id, "message": message, "status": "sent"}

    async def message_ask_user(self, user_id: str, prompt: str) -> Dict[str, Any]:
        return {"user_id": user_id, "prompt": prompt, "status": "awaiting"}

    # ------------------------------------------------------------------
    # Shell helpers
    # ------------------------------------------------------------------
    async def shell_exec(self, command: str, session_id: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._shell_processes[session_id] = process
        self._shell_tasks[session_id] = asyncio.create_task(process.communicate())
        self._shell_results.pop(session_id, None)
        return {"session": session_id, "status": "running"}

    async def shell_wait(self, session_id: str) -> Dict[str, Any]:
        if session_id in self._shell_results:
            return self._shell_results[session_id]

        process = self._shell_processes.get(session_id)
        task = self._shell_tasks.get(session_id)
        if not process or not task:
            LOGGER.error("shell_wait: session '%s' not found", session_id)
            return {"error": "session not found"}

        stdout, stderr = await task
        returncode = process.returncode
        if returncode is None:
            returncode = await process.wait()
        result = {
            "stdout": stdout.decode(errors="ignore"),
            "stderr": stderr.decode(errors="ignore"),
            "returncode": returncode,
        }
        self._shell_results[session_id] = result
        return result

    async def shell_kill(self, session_id: str) -> Dict[str, Any]:
        process = self._shell_processes.get(session_id)
        if not process:
            return {"error": "session not found"}
        if process.returncode is None:
            process.kill()
            await process.wait()
            return {"session": session_id, "status": "killed"}
        return {"session": session_id, "status": "finished"}

    async def shell_view(self, session_id: str) -> Dict[str, Any]:
        if session_id in self._shell_results:
            result = self._shell_results[session_id]
            return {"status": "finished", **result}
        process = self._shell_processes.get(session_id)
        if not process:
            return {"error": "session not found"}
        status = "running" if process.returncode is None else "finished"
        return {"session": session_id, "status": status}

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------
    async def file_read(self, path: str) -> Dict[str, Any]:
        resolved = self._resolve_path(path)
        if resolved is None:
            return {"error": "access denied"}
        if not resolved.exists():
            return {"error": "file not found"}
        content = await asyncio.to_thread(resolved.read_text)
        return {"path": str(resolved), "content": content}

    async def file_append_text(self, path: str, text: str) -> Dict[str, Any]:
        resolved = self._resolve_path(path)
        if resolved is None:
            return {"error": "access denied"}
        await asyncio.to_thread(resolved.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(self._append_text, resolved, text)
        return {"path": str(resolved), "status": "appended"}

    @staticmethod
    def _append_text(path: Path, text: str) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)

    async def file_replace_text(self, path: str, target: str, replacement: str) -> Dict[str, Any]:
        resolved = self._resolve_path(path)
        if resolved is None:
            return {"error": "access denied"}
        if not resolved.exists():
            return {"error": "file not found"}
        content = await asyncio.to_thread(resolved.read_text)
        new_content = content.replace(target, replacement)
        await asyncio.to_thread(resolved.write_text, new_content)
        return {"path": str(resolved), "status": "replaced"}

    # ------------------------------------------------------------------
    # Media helpers
    # ------------------------------------------------------------------
    async def media_generate_image(self, prompt: str, output_path: str) -> Dict[str, Any]:
        resolved = self._resolve_path(output_path)
        if resolved is None:
            return {"error": "access denied"}
        await asyncio.to_thread(resolved.parent.mkdir, parents=True, exist_ok=True)

        image_module = _import_optional("PIL.Image")
        draw_module = _import_optional("PIL.ImageDraw")
        if image_module is not None and draw_module is not None:
            def _render() -> None:
                image = image_module.new("RGB", (512, 512), color=(255, 255, 255))
                draw = draw_module.Draw(image)
                draw.text((10, 10), prompt[:100], fill=(0, 0, 0))
                image.save(resolved)

            try:
                await asyncio.to_thread(_render)
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.warning("Image rendering failed, writing fallback: %s", exc)
                await asyncio.to_thread(resolved.write_text, f"Prompt: {prompt}\n")
        else:
            await asyncio.to_thread(resolved.write_text, f"Prompt: {prompt}\n")

        return {"path": str(resolved), "prompt": prompt}

    async def media_generate_speech(self, text: str, output_path: str) -> Dict[str, Any]:
        return {"error": "text-to-speech is not available in this environment", "path": output_path}

    async def media_analyze_image(self, image_path: str) -> Dict[str, Any]:
        resolved = self._resolve_path(image_path)
        if resolved is None:
            return {"error": "file not found"}

        pytesseract_module = _import_optional("pytesseract")
        image_module = _import_optional("PIL.Image")
        if pytesseract_module is None or image_module is None:
            return {"error": "OCR dependencies not available"}

        def _ocr() -> str:
            image = image_module.open(resolved)
            try:
                return pytesseract_module.image_to_string(image)
            finally:
                close = getattr(image, "close", None)
                if close:
                    close()

        try:
            text = await asyncio.to_thread(_ocr)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("media_analyze_image failed: %s", exc)
            return {"error": str(exc)}
        return {"text": text}

    async def media_recognize_speech(self, audio_path: str) -> Dict[str, Any]:
        resolved = self._resolve_path(audio_path)
        if resolved is None:
            return {"error": "file not found"}

        sr_module = _import_optional("speech_recognition")
        if sr_module is None:
            return {"error": "speech recognition library not available"}

        recognizer = sr_module.Recognizer()

        def _recognise() -> str:
            with sr_module.AudioFile(str(resolved)) as source:
                audio = recognizer.record(source)
            return recognizer.recognize_sphinx(audio)

        try:
            text = await asyncio.to_thread(_recognise)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("media_recognize_speech failed: %s", exc)
            return {"error": str(exc)}
        return {"text": text}

    async def media_analyze_video(self, video_path: str) -> Dict[str, Any]:
        resolved = self._resolve_path(video_path)
        if resolved is None:
            return {"error": "file not found"}

        cv2_module = _import_optional("cv2")
        if cv2_module is None:
            return {"error": "video analysis dependencies not available"}

        def _analyse() -> Optional[Dict[str, Any]]:
            capture = cv2_module.VideoCapture(str(resolved))
            try:
                if not capture.isOpened():
                    return None
                frame_prop = getattr(cv2_module, "CAP_PROP_FRAME_COUNT", 7)
                fps_prop = getattr(cv2_module, "CAP_PROP_FPS", 5)
                width_prop = getattr(cv2_module, "CAP_PROP_FRAME_WIDTH", 3)
                height_prop = getattr(cv2_module, "CAP_PROP_FRAME_HEIGHT", 4)
                frames = int(capture.get(frame_prop) or 0)
                fps = float(capture.get(fps_prop) or 0.0)
                width = int(capture.get(width_prop) or 0)
                height = int(capture.get(height_prop) or 0)
            finally:
                capture.release()
            duration = frames / fps if fps else 0.0
            return {
                "frames": frames,
                "fps": fps,
                "duration": duration,
                "width": width,
                "height": height,
            }

        details = await asyncio.to_thread(_analyse)
        if details is None:
            return {"error": "unable to open video"}
        return details

    async def media_describe_video(self, video_path: str, sample_frames: int = 5) -> Dict[str, Any]:
        resolved = self._resolve_path(video_path)
        if resolved is None:
            return {"error": "file not found"}

        cv2_module = _import_optional("cv2")
        if cv2_module is None:
            return {"error": "video analysis dependencies not available"}

        def _describe() -> Optional[Dict[str, Any]]:
            capture = cv2_module.VideoCapture(str(resolved))
            try:
                if not capture.isOpened():
                    return None
                collected: List[List[float]] = []
                count = 0
                while count < sample_frames:
                    ret, frame = capture.read()
                    if not ret:
                        break
                    mean = frame.mean(axis=(0, 1)) if hasattr(frame, "mean") else [0.0, 0.0, 0.0]
                    collected.append([float(x) for x in mean])
                    count += 1
            finally:
                capture.release()
            if not collected:
                return {"avg_color": [0.0, 0.0, 0.0]}
            avg = [sum(channel) / len(collected) for channel in zip(*collected)]
            return {"avg_color": [float(x) for x in avg]}

        description = await asyncio.to_thread(_describe)
        if description is None:
            return {"error": "unable to open video"}
        return description

    # ------------------------------------------------------------------
    # Information search helpers
    # ------------------------------------------------------------------
    async def info_search_web(self, query: str) -> Dict[str, Any]:
        params = {"q": query}
        try:
            async with aiohttp.ClientSession() as session:
                request = self._session_get(session, "https://duckduckgo.com/html/", params=params)
                async with request as resp:
                    text = await resp.text()
        except Exception as exc:
            LOGGER.warning("info_search_web failed: %s", exc)
            return {"results": [], "error": str(exc)}

        pattern = re.compile(r"<a[^>]+class=['\"]result__a['\"][^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", re.IGNORECASE)
        results = []
        for url, title in pattern.findall(text):
            clean_title = re.sub(r"<.*?>", "", title)
            results.append({"title": clean_title, "url": url})
        return {"results": results}

    async def info_search_api(self, url: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        response_payload: Optional[Any] = None
        try:
            async with aiohttp.ClientSession() as session:
                request = self._session_get(session, url, params=params)
                async with request as resp:
                    try:
                        response_payload = await resp.json(content_type=None)
                    except TypeError:
                        response_payload = await resp.json()
        except Exception as exc:
            LOGGER.warning("info_search_api failed: %s", exc)
            return {"response": response_payload, "error": str(exc)}
        return {"response": response_payload}

    async def info_search_image(self, query: str) -> Dict[str, Any]:
        params = {"query": query, "per_page": 5}
        try:
            async with aiohttp.ClientSession() as session:
                request = self._session_get(session, "https://api.unsplash.com/search/photos", params=params)
                async with request as resp:
                    try:
                        data = await resp.json(content_type=None)
                    except TypeError:
                        data = await resp.json()
        except Exception as exc:
            LOGGER.warning("info_search_image failed: %s", exc)
            return {"results": [], "error": str(exc)}

        formatted = []
        for item in data.get("results", []):
            urls = item.get("urls", {})
            formatted.append(
                {
                    "id": item.get("id"),
                    "description": item.get("alt_description"),
                    "url": urls.get("small"),
                }
            )
        if not formatted:
            return {"results": [], "error": "no results"}
        return {"results": formatted}

    # ------------------------------------------------------------------
    # Browser/service placeholders
    # ------------------------------------------------------------------
    async def browser_navigate(self, url: str) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "url": url}

    async def browser_view(self) -> Dict[str, Any]:
        return {"error": "browser automation not supported"}

    async def browser_click(self, selector: str) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "selector": selector}

    async def browser_input(self, selector: str, text: str) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "selector": selector}

    async def browser_move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "x": x, "y": y}

    async def browser_press_key(self, key: str) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "key": key}

    async def browser_select_option(self, selector: str, option: str) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "selector": selector}

    async def browser_save_image(self, selector: str) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "selector": selector}

    async def browser_scroll_up(self) -> Dict[str, Any]:
        return {"error": "browser automation not supported"}

    async def browser_scroll_down(self) -> Dict[str, Any]:
        return {"error": "browser automation not supported"}

    async def browser_console_exec(self, script: str) -> Dict[str, Any]:
        return {"error": "browser automation not supported", "script": script}

    async def browser_console_view(self) -> Dict[str, Any]:
        return {"error": "browser automation not supported"}

    async def service_expose_port(self, port: int) -> Dict[str, Any]:
        return {"error": "service deployment not supported", "port": port}

    async def service_deploy_frontend(self, project: str) -> Dict[str, Any]:
        return {"error": "service deployment not supported", "project": project}

    async def service_deploy_backend(self, project: str) -> Dict[str, Any]:
        return {"error": "service deployment not supported", "project": project}

    # ------------------------------------------------------------------
    # Slide helpers
    # ------------------------------------------------------------------
    async def slide_initialize(self, project_path: str) -> Dict[str, Any]:
        resolved = self._resolve_path(project_path)
        if resolved is None:
            return {"error": "access denied"}
        await asyncio.to_thread(resolved.mkdir, parents=True, exist_ok=True)
        outline_file = resolved / "slides.txt"
        if not outline_file.exists():
            await asyncio.to_thread(outline_file.write_text, "Slide 1: Title\n", "utf-8")
        return {"project": str(resolved)}

    async def slide_present(self, project_path: str) -> Dict[str, Any]:
        resolved = self._resolve_path(project_path)
        if resolved is None or not resolved.exists():
            return {"error": "project not found"}
        return {"project": str(resolved), "status": "presenting"}

    # ------------------------------------------------------------------
    # Legacy convenience wrappers
    # ------------------------------------------------------------------
    def get_tool_by_name(self, name: str):
        return self.tools.get(name)

    async def respond_to_user(self, text: str) -> str:
        return text

    async def generate_image(self, prompt: str, **kwargs: Any) -> str:
        result = await self.media_generate_image(prompt, kwargs.get("output_path", "generated.png"))
        return result.get("path", "")

    async def simple_math(self, expression: str) -> str:
        allowed_chars = set("0123456789+-*/(). ")
        if any(ch not in allowed_chars for ch in expression):
            return "エラー: 許可されていない文字が含まれています。"
        try:
            result = eval(expression, {"__builtins__": {}}, {})
        except Exception as exc:  # pragma: no cover - defensive
            return f"計算エラー: {exc}"
        return f"計算結果: {result}"

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
                            "output_path": {"type": "string"},
                        },
                        "required": ["prompt"],
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
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "simple_math",
                    "description": "簡単な計算を行います。",
                    "parameters": {
                        "type": "object",
                        "properties": {"expression": {"type": "string"}},
                        "required": ["expression"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "現在の日時を返します。",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]
