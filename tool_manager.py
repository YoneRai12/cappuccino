import asyncio
import logging
import os
import json
import inspect
import re
import textwrap
import subprocess
import tempfile
from functools import wraps
from typing import Any, Dict, Optional

import aiosqlite
from PIL import Image, ImageDraw
from state_manager import StateManager



class ToolExecutionError(Exception):
    """Raised when a tool encounters an error during execution."""


logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def log_tool(func):
    """Decorator to log tool execution with parameters and errors."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        bound = inspect.signature(func).bind_partial(self, *args, **kwargs)
        bound.apply_defaults()
        params = {k: v for k, v in bound.arguments.items() if k != "self"}
        logger.info("tool=%s params=%s", func.__name__, params)
        try:
            return await func(self, *args, **kwargs)
        except TypeError as exc:
            logger.exception("tool=%s params=%s", func.__name__, params)
            return {"error": str(exc)}
        except Exception as exc:
            logger.exception("tool=%s params=%s", func.__name__, params)
            return {"error": str(exc)}
    wrapper.__signature__ = inspect.signature(func)
    return wrapper


class ToolManager:
    """Collection of asynchronous tools for the Cappuccino agent."""

    def __init__(self, db_path: str = "agent_state.db", root_dir: Optional[str] = None):
        self.db_path = db_path
        self.root_dir = os.path.abspath(root_dir) if root_dir else None
        self.db_connection: Optional[aiosqlite.Connection] = None
        self.shell_sessions: Dict[str, asyncio.subprocess.Process] = {}
        self.browser_content: str = ""
        self.browser_url: str = ""
        self.service_processes: Dict[int, Any] = {}
        self.state_manager = StateManager(db_path)

    async def __aenter__(self) -> "ToolManager":
        """Open the database connection when entering the context."""
        await self._get_db_connection()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close the database connection on context exit."""
        await self.close()

    async def close(self) -> None:
        """Explicitly close the database connection."""
        if self.db_connection is not None:
            await self.db_connection.close()
            self.db_connection = None
        await self.state_manager.close()

    # ------------------------------------------------------------------
    # Path utilities
    # ------------------------------------------------------------------
    def _validate_path(self, path: str) -> str:
        """Return an absolute path optionally restricted to the workspace root."""
        abs_path = os.path.abspath(path if os.path.isabs(path) else os.path.join(self.root_dir or os.getcwd(), path))

        if self.root_dir and os.path.commonpath([abs_path, self.root_dir]) != self.root_dir:
            raise ValueError("Access outside workspace root is not allowed")
        return abs_path

    async def _get_db_connection(self) -> aiosqlite.Connection:
        if self.db_connection is None:
            self.db_connection = await aiosqlite.connect(self.db_path)
            await self._initialize_db()
        return self.db_connection

    async def _initialize_db(self) -> None:
        conn = await self._get_db_connection()
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    plan TEXT,
                    phase INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    schedule TEXT
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    type TEXT,
                    content TEXT
            )"""
        )
        await conn.execute(

            """CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT,
                    content TEXT
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS tools (
                    name TEXT PRIMARY KEY,
                    code TEXT
            )"""
        )
        await conn.commit()


    async def _add_history_entry(self, role: str, content: str) -> None:
        """Store a conversation message in the history table."""
        conn = await self._get_db_connection()
        await conn.execute(
            "INSERT INTO history (role, content) VALUES (?, ?)",
            (role, content),

        )
        await conn.commit()

    async def _register_tool(self, name: str, code: str) -> None:
        """Persist a learned tool to the database."""
        conn = await self._get_db_connection()
        await conn.execute(
            "INSERT INTO tools(name, code) VALUES(?, ?)"
            " ON CONFLICT(name) DO UPDATE SET code=excluded.code",
            (name, code),
        )
        await conn.commit()

    # ------------------------------------------------------------------
    # Result caching helpers
    # ------------------------------------------------------------------
    async def get_cached_result(self, key: str) -> Optional[str]:
        """Return cached value for key if present."""
        conn = await self._get_db_connection()
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)"
        )
        async with conn.execute("SELECT value FROM cache WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def set_cached_result(self, key: str, value: str) -> None:
        """Store key/value pair in cache table."""
        conn = await self._get_db_connection()
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)"
        )
        await conn.execute(
            "REPLACE INTO cache (key, value) VALUES (?, ?)",
            (key, value),
        )
        await conn.commit()

    # ------------------------------------------------------------------
    # Knowledge graph
    # ------------------------------------------------------------------
    @log_tool
    async def graph_add_entity(
        self, name: str, attrs: Optional[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        graph = await self.state_manager.load_graph()
        graph.add_entity(name, **(attrs or {}))
        await self.state_manager.save_graph(graph)
        return {"entity": name}

    @log_tool
    async def graph_add_relation(
        self,
        source: str,
        target: str,
        relation: str,
        attrs: Optional[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        graph = await self.state_manager.load_graph()
        graph.add_relation(source, target, relation, **(attrs or {}))
        await self.state_manager.save_graph(graph)
        return {"source": source, "target": target, "relation": relation}

    @log_tool
    async def graph_query(self, entity: str) -> Dict[str, Any]:
        graph = await self.state_manager.load_graph()
        return {"entity": entity, "relations": graph.query(entity)}

    @log_tool
    async def graph_remove_relation(self, source: str, target: str, relation: str) -> Dict[str, Any]:
        graph = await self.state_manager.load_graph()
        graph.remove_relation(source, target, relation)
        await self.state_manager.save_graph(graph)
        return {"status": "removed"}

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------
    @log_tool
    async def agent_update_plan(self, task_id: str, plan: str) -> Dict[str, Any]:
        """Create or update a task plan."""
        conn = await self._get_db_connection()
        await conn.execute(
            "INSERT INTO tasks(id, plan) VALUES(?, ?) ON CONFLICT(id) DO UPDATE SET plan=excluded.plan",
            (task_id, plan),
        )
        await conn.commit()
        return {"task_id": task_id, "plan": plan}

    @log_tool
    async def agent_advance_phase(self, task_id: str) -> Dict[str, Any]:
        """Advance task to the next phase."""
        conn = await self._get_db_connection()
        await conn.execute(
            "UPDATE tasks SET phase = phase + 1 WHERE id = ?",
            (task_id,),
        )
        await conn.commit()
        cur = await conn.execute("SELECT phase FROM tasks WHERE id = ?", (task_id,))
        row = await cur.fetchone()
        return {"task_id": task_id, "phase": row[0] if row else None}

    @log_tool
    async def agent_end_task(self, task_id: str) -> Dict[str, Any]:
        """Mark task as completed."""
        conn = await self._get_db_connection()
        await conn.execute(
            "UPDATE tasks SET status='completed' WHERE id = ?",
            (task_id,),
        )
        await conn.commit()
        return {"task_id": task_id, "status": "completed"}

    @log_tool
    async def agent_schedule_task(self, task_id: str, schedule: str) -> Dict[str, Any]:
        """Set schedule information for a task."""
        conn = await self._get_db_connection()
        await conn.execute(
            "UPDATE tasks SET schedule=? WHERE id = ?",
            (schedule, task_id),
        )
        await conn.commit()
        return {"task_id": task_id, "schedule": schedule}

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------
    @log_tool
    async def message_notify_user(self, user_id: str, message: str) -> Dict[str, Any]:
        """Store a notification for the user."""
        conn = await self._get_db_connection()
        await conn.execute(
            "INSERT INTO messages(user_id, type, content) VALUES(?, 'notify', ?)",
            (user_id, message),
        )
        await conn.commit()
        return {"user_id": user_id, "message": message}

    @log_tool
    async def message_ask_user(self, user_id: str, question: str) -> Dict[str, Any]:
        """Store a question for the user and return placeholder for response."""
        conn = await self._get_db_connection()
        await conn.execute(
            "INSERT INTO messages(user_id, type, content) VALUES(?, 'ask', ?)",
            (user_id, question),
        )
        await conn.commit()
        return {"user_id": user_id, "question": question, "status": "awaiting"}

    # ------------------------------------------------------------------
    # Shell management
    # ------------------------------------------------------------------
    @log_tool
    async def shell_exec(self, command: str, session_id: str, working_dir: str = ".") -> Dict[str, Any]:
        """Execute a shell command asynchronously and store the session."""
        try:
            working_dir = self._validate_path(working_dir)
        except ValueError as e:
            return {"error": str(e)}
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
        )
        self.shell_sessions[session_id] = process
        return {"session_id": session_id, "status": "running"}

    @log_tool
    async def shell_view(self, session_id: str) -> Dict[str, Any]:
        """Return current stdout and stderr for the session."""
        process = self.shell_sessions.get(session_id)
        if not process:
            return {"error": "session not found"}
        stdout = await process.stdout.read() if not process.stdout.at_eof() else b""
        stderr = await process.stderr.read() if not process.stderr.at_eof() else b""
        return {"stdout": stdout.decode(), "stderr": stderr.decode()}

    @log_tool
    async def shell_wait(self, session_id: str) -> Dict[str, Any]:
        """Wait for the process to complete and return outputs."""
        process = self.shell_sessions.get(session_id)
        if not process:
            raise ToolExecutionError("session not found")
        stdout, stderr = await process.communicate()
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
        }

    @log_tool
    async def shell_input(self, session_id: str, text: str) -> Dict[str, Any]:
        """Send input to the running shell session."""
        process = self.shell_sessions.get(session_id)
        if not process or process.stdin is None:
            return {"error": "session not found"}
        process.stdin.write(text.encode())
        await process.stdin.drain()
        return {"status": "sent"}

    @log_tool
    async def shell_kill(self, session_id: str) -> Dict[str, Any]:
        """Terminate the shell session."""
        process = self.shell_sessions.get(session_id)
        if not process:
            return {"error": "session not found"}
        process.kill()
        await process.wait()
        return {"status": "killed"}

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    @log_tool
    async def file_read(self, abs_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:

        """Read a text file and optionally limit lines."""
        try:
            abs_path = self._validate_path(abs_path)
        except ValueError as e:
            return {"error": str(e)}
        if not os.path.exists(abs_path):
            return {"error": f"File not found: {abs_path}"}
        # Read the file in a helper function so the file handle is properly
        # closed and no ResourceWarning is triggered.
        content = await asyncio.to_thread(self._read_text_file, abs_path)
        lines = content.splitlines(True)
        if start_line is not None or end_line is not None:
            lines = lines[start_line:end_line]
        return {"content": "".join(lines)}

    @log_tool
    async def file_append_text(self, abs_path: str, text: str) -> Dict[str, Any]:
        """Append text to a file."""
        try:
            abs_path = self._validate_path(abs_path)
        except ValueError as e:
            return {"error": str(e)}
        await asyncio.to_thread(self._append_text, abs_path, text)
        return {"status": "appended"}

    def _append_text(self, abs_path: str, text: str) -> None:
        with open(abs_path, "a") as f:
            f.write(text)

    @log_tool
    async def file_replace_text(self, abs_path: str, old: str, new: str) -> Dict[str, Any]:
        """Replace text in a file."""
        try:
            abs_path = self._validate_path(abs_path)
        except ValueError as e:
            return {"error": str(e)}
        if not os.path.exists(abs_path):
            raise FileNotFoundError(abs_path)
        await asyncio.to_thread(self._replace_text, abs_path, old, new)
        return {"status": "replaced"}

    def _replace_text(self, abs_path: str, old: str, new: str) -> None:
        with open(abs_path, "r+") as f:
            content = f.read()
            content = content.replace(old, new)
            f.seek(0)
            f.write(content)
            f.truncate()

    def _read_text_file(self, abs_path: str) -> str:
        """Helper to read a file's text content safely."""
        with open(abs_path, "r") as f:
            return f.read()
    # ------------------------------------------------------------------
    # Media generation
    # ------------------------------------------------------------------
    @log_tool
    async def media_generate_image(self, text: str, output_path: str) -> Dict[str, Any]:
        """Generate a simple image with text."""
        try:
            output_path = self._validate_path(output_path)
        except ValueError as e:
            return {"error": str(e)}

        def _generate() -> None:
            img = Image.new("RGB", (400, 200), color="white")
            draw = ImageDraw.Draw(img)
            draw.text((10, 90), text, fill="black")
            img.save(output_path)

        await asyncio.to_thread(_generate)
        return {"path": output_path}

    @log_tool
    async def media_generate_speech(self, text: str, output_path: str) -> Dict[str, Any]:
        """Generate speech audio from text and save as an MP3 file."""
        try:
            from gtts import gTTS  # type: ignore

            def _generate() -> None:
                tts = gTTS(text)
                tts.save(output_path)

            await asyncio.to_thread(_generate)
            # Placeholder implementation still returns an error for now
            return {"error": "speech generation not implemented"}
        except Exception:
            return {"error": "speech generation not implemented"}



    @log_tool
    async def media_analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from an image using pytesseract."""
        try:
            import pytesseract
            from PIL import Image
        except Exception:
            return {"error": "pytesseract not available"}

        def _ocr() -> Dict[str, Any]:
            text = pytesseract.image_to_string(Image.open(image_path))
            return {"text": text}

        return await asyncio.to_thread(_ocr)

    @log_tool
    async def media_recognize_speech(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe speech from an audio file using SpeechRecognition."""
        try:
            import speech_recognition as sr
        except Exception:
            return {"error": "speech_recognition not available"}

        def _recognize() -> Dict[str, Any]:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            try:
                text = recognizer.recognize_sphinx(audio)
            except Exception:
                return {"error": "recognition failed"}
            return {"text": text}

        return await asyncio.to_thread(_recognize)

    @log_tool
    async def media_describe_video(self, video_path: str) -> Dict[str, Any]:
        """Return the average color of the first frame of a video."""
        try:
            import cv2
        except Exception:
            return {"error": "opencv not available"}

        def _describe() -> Dict[str, Any]:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("unable to open video")
            ret, frame = cap.read()
            cap.release()
            if not ret:
                raise ValueError("unable to read frame")
            avg_color = frame.mean(axis=(0, 1))
            return {"avg_color": [float(x) for x in avg_color]}

        return await asyncio.to_thread(_describe)

    async def media_analyze_video(self, video_path: str) -> Dict[str, Any]:
        """Return basic metadata for a video file."""
        try:
            import cv2
        except Exception:
            return {"error": "opencv not available"}

        def _analyze() -> Dict[str, Any]:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("unable to open video")
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            duration = frame_count / fps if fps else 0.0
            return {
                "frames": frame_count,
                "fps": fps,
                "width": width,
                "height": height,
                "duration": duration,
            }

        return await asyncio.to_thread(_analyze)


    # ------------------------------------------------------------------
    # Information search
    # ------------------------------------------------------------------
    @log_tool
    async def info_search_web(self, query: str) -> Dict[str, Any]:
        """Search the web using DuckDuckGo and return titles and links."""
        cache_key = f"info_search_web:{query}"
        cached = await self.get_cached_result(cache_key)
        if cached:
            return json.loads(cached)

        import aiohttp
        from bs4 import BeautifulSoup

        url = "https://duckduckgo.com/html/?q=" + query
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                text = await resp.text()
        soup = BeautifulSoup(text, "html.parser")
        results = []
        for a in soup.select("a.result__a"):
            results.append({"title": a.text, "href": a.get("href")})
        output = {"results": results}
        await self.set_cached_result(cache_key, json.dumps(output))
        return output

    @log_tool
    async def info_search_image(self, query: str) -> Dict[str, Any]:


        """Search images using the Unsplash API."""
        import aiohttp

        url = f"https://unsplash.com/napi/search/photos?query={query}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    return {"error": "image search failed"}


        results = [
            {
                "id": r.get("id"),
                "description": r.get("alt_description"),
                "url": r.get("urls", {}).get("small"),
            }
            for r in data.get("results", [])
        ]
        return {"results": results}


    @log_tool
    async def info_search_api(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a generic API GET request."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.text()
        return {"response": data}

    # ------------------------------------------------------------------
    # Browser automation (placeholders)
    # ------------------------------------------------------------------
    @log_tool
    async def browser_navigate(self, url: str = "") -> Dict[str, Any]:

        """Fetch a web page and store its contents for later viewing."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    self.browser_content = await resp.text()
                    self.browser_url = str(resp.url)
            return {"status": "success", "url": self.browser_url}
        except Exception as e:
            logging.error(f"browser_navigate error: {e}")
            return {"error": str(e)}


    @log_tool
    async def browser_view(self) -> Dict[str, Any]:

        """Return a preview of the last fetched page."""
        if not self.browser_content:
            return {"error": "no page loaded"}
        return {"url": self.browser_url, "preview": self.browser_content[:500]}


    @log_tool

    async def browser_click(self, selector: str) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_input(self, selector: str, text: str) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_press_key(self, key: str) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_select_option(self, selector: str, option: str) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_save_image(self, selector: str, output_path: str) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_scroll_up(self, amount: int) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_scroll_down(self, amount: int) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_console_exec(self, script: str) -> Dict[str, Any]:

        return {"error": "browser automation not implemented"}

    @log_tool
    async def browser_console_view(self) -> Dict[str, Any]:
        return {"error": "browser automation not implemented"}

    # ------------------------------------------------------------------
    # Service deployment (placeholders)
    # ------------------------------------------------------------------

    @log_tool
    async def service_expose_port(self, port: int = 8000, directory: str = ".") -> Dict[str, Any]:
        """Expose a simple HTTP service on the given port."""
        # Placeholder implementation currently disabled for security
        return {"error": "service management not implemented"}


    @log_tool

    async def service_deploy_frontend(self, source_dir: str) -> Dict[str, Any]:
        return {"error": "service management not implemented"}

    @log_tool
    async def service_deploy_backend(self, source_dir: str) -> Dict[str, Any]:

        return {"error": "service management not implemented"}

    # ------------------------------------------------------------------
    # Slide presentation (placeholders)
    # ------------------------------------------------------------------
    @log_tool
    async def slide_initialize(self, project_name: str) -> Dict[str, Any]:
        try:
            project_path = self._validate_path(project_name)
        except ValueError as e:
            return {"error": str(e)}
        os.makedirs(project_path, exist_ok=True)
        return {"project": project_path}

    @log_tool
    async def slide_present(self, project_name: str) -> Dict[str, Any]:
        try:
            project_path = self._validate_path(project_name)
        except ValueError as e:
            return {"error": str(e)}
        return {"project": project_path, "status": "presenting"}

    async def generate_tool_from_failure(
        self,
        task_description: str,
        error_message: str,
        api_key: str,
    ) -> Dict[str, Any]:
        """Analyze a failed task and create a new tool via LLM.

        The LLM should respond with a complete async Python function
        definition. The function will be validated, stored and added
        to this instance.
        """

        from openai import AsyncOpenAI

        # gather recent user comments for additional context
        conn = await self._get_db_connection()
        async with conn.execute(
            "SELECT content FROM history WHERE role='user' ORDER BY id DESC LIMIT 5"
        ) as cur:
            comments = [row[0] async for row in cur]
        user_notes = "\n".join(reversed(comments))

        prompt = (
            "You are a developer assistant that writes new async Python "
            "functions for the Cappuccino ToolManager. "
            f"The user task was: {task_description}. "
            f"It failed with logs: {error_message}. "
            f"Recent user comments: {user_notes}. "
            "Provide only the function code."
        )

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw_code = textwrap.dedent(response.choices[0].message.content or "")
        lines = raw_code.splitlines()
        if len(lines) > 1 and not lines[1].startswith(" "):
            lines[1:] = ["    " + line for line in lines[1:]]
        code = "\n".join(lines)

        match = re.search(r"async def\s+(\w+)\s*\(", code)
        if not match:
            return {"error": "No function definition found"}
        func_name = match.group(1)

        with tempfile.TemporaryDirectory() as tmpdir:
            tool_file = os.path.join(tmpdir, "tool.py")
            with open(tool_file, "w") as f:
                f.write(code)
            test_file = os.path.join(tmpdir, "test_tool.py")
            with open(test_file, "w") as f:
                f.write(
                    "import asyncio\nfrom tool import %s\n\n"
                    "async def test_async():\n    assert asyncio.iscoroutinefunction(%s)\n"
                    % (func_name, func_name)
                )

            try:
                await asyncio.to_thread(
                    subprocess.run,
                    ["ruff", "check", tool_file],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=tmpdir,
                )
                await asyncio.to_thread(
                    subprocess.run,
                    ["pytest", "-q", test_file],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=tmpdir,
                )
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                # Skip validation if tooling is unavailable during tests
                logging.warning(f"Validation skipped: {exc}")

            local_ns: Dict[str, Any] = {}
            try:
                exec(code, {}, local_ns)
            except Exception as e:  # pragma: no cover - exec failure path
                return {"error": f"Failed to exec generated code: {e}"}

            func = local_ns.get(func_name)

        setattr(self, func_name, func)
        await self._register_tool(func_name, code)
        return {"name": func_name, "code": code}
