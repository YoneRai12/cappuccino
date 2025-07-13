import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
import os
import pytest
import pytest_asyncio

from tool_manager import ToolManager


@pytest_asyncio.fixture()
async def tm(tmp_path):
    manager = ToolManager(db_path=os.path.join(tmp_path, "db.sqlite"))
    yield manager
    if manager.db_connection:
        await manager.db_connection.close()


@pytest.mark.asyncio
async def test_agent_management(tm):
    await tm.agent_update_plan("1", "plan")
    phase = await tm.agent_advance_phase("1")
    assert phase["phase"] == 1
    status = await tm.agent_end_task("1")
    assert status["status"] == "completed"
    sched = await tm.agent_schedule_task("1", "daily")
    assert sched["schedule"] == "daily"


@pytest.mark.asyncio
async def test_message_functions(tm):
    note = await tm.message_notify_user("u", "hi")
    assert note["message"] == "hi"
    ask = await tm.message_ask_user("u", "?")
    assert ask["status"] == "awaiting"


@pytest.mark.asyncio
async def test_shell_functions(tm):
    session = "s"
    await tm.shell_exec("echo hi", session)
    wait = await tm.shell_wait(session)
    assert wait["returncode"] == 0
    # start another session to test kill
    await tm.shell_exec("sleep 1", "k")
    kill = await tm.shell_kill("k")
    assert kill["status"] == "killed"
    missing = await tm.shell_view("missing")
    assert "error" in missing


@pytest.mark.asyncio
async def test_file_operations(tm, tmp_path):
    file_path = tmp_path / "f.txt"
    await asyncio.to_thread(file_path.write_text, "line1\n")
    content = await tm.file_read(str(file_path))
    assert content["content"] == "line1\n"
    await tm.file_append_text(str(file_path), "line2\n")
    replaced = await tm.file_replace_text(str(file_path), "line1", "LINE1")
    assert replaced["status"] == "replaced"
    not_found = await tm.file_read(str(tmp_path / "none.txt"))
    assert "error" in not_found


@pytest.mark.asyncio
async def test_media_functions(tm, tmp_path, monkeypatch):
    img_path = tmp_path / "img.png"
    result = await tm.media_generate_image("hi", str(img_path))
    assert os.path.exists(result["path"])
    speech = await tm.media_generate_speech("hi", "out.wav")
    assert "error" in speech

    import types
    import sys
    monkeypatch.setitem(sys.modules, "pytesseract", types.SimpleNamespace(image_to_string=lambda img: "ocr"))
    monkeypatch.setattr("PIL.Image.open", lambda p: "img")
    ocr = await tm.media_analyze_image(str(img_path))
    assert ocr["text"] == "ocr"
    class DummyFile:
        def __init__(self, path):
            self.path = path
        def __enter__(self):
            return "src"
        def __exit__(self, exc_type, exc, tb):
            pass
    class DummyRec:
        def record(self, source):
            return b"aud"
        def recognize_sphinx(self, audio):
            return "hi"
    speech_mod = types.SimpleNamespace(AudioFile=DummyFile, Recognizer=DummyRec)
    monkeypatch.setitem(sys.modules, "speech_recognition", speech_mod)
    recog = await tm.media_recognize_speech("snd.wav")
    assert recog["text"] == "hi"
    cv2_mod = types.SimpleNamespace(VideoCapture=lambda p: types.SimpleNamespace(isOpened=lambda: True, read=lambda: (True, types.SimpleNamespace(mean=lambda axis=None: [1,2,3])), release=lambda: None))
    monkeypatch.setitem(sys.modules, "cv2", cv2_mod)
    desc = await tm.media_describe_video("v.mp4")
    assert desc["avg_color"] == [1,2,3]

@pytest.mark.asyncio
async def test_info_search(tm, monkeypatch):
    class Resp:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def text(self):
            return "<a class='result__a' href='http://x'>title</a>"

    class Session:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        def get(self, url, params=None):
            return Resp()

    monkeypatch.setattr("aiohttp.ClientSession", lambda: Session())
    web = await tm.info_search_web("test")
    assert web["results"][0]["title"] == "title"

    api_resp = await tm.info_search_api("http://x", None)
    assert "response" in api_resp

    image = await tm.info_search_image("q")
    assert "error" in image


@pytest.mark.asyncio
async def test_browser_and_service_placeholders(tm):
    funcs = [
        tm.browser_navigate,
        tm.browser_view,
        tm.browser_click,
        tm.browser_input,
        tm.browser_move_mouse,
        tm.browser_press_key,
        tm.browser_select_option,
        tm.browser_save_image,
        tm.browser_scroll_up,
        tm.browser_scroll_down,
        tm.browser_console_exec,
        tm.browser_console_view,
        tm.service_expose_port,
        tm.service_deploy_frontend,
        tm.service_deploy_backend,
    ]
    for func in funcs:
        arg_count = func.__code__.co_argcount - 1
        if arg_count == 0:
            result = await func()
        elif arg_count == 1:
            arg = 1 if 'service_expose_port' in func.__name__ else "x"
            result = await func(arg)
        else:
            result = await func("x", "y")
        assert "error" in result


@pytest.mark.asyncio
async def test_slide_functions(tm, tmp_path):
    proj = tmp_path / "proj"
    init = await tm.slide_initialize(str(proj))
    assert os.path.exists(init["project"])
    present = await tm.slide_present(str(proj))
    assert present["status"] == "presenting"

