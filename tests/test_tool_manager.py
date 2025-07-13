import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import asyncio
import os

import logging
import pytest

from tool_manager import ToolManager
import cv2

@pytest.mark.asyncio
async def test_file_read_and_append(tmp_path):

    async with ToolManager(db_path=os.path.join(tmp_path, "db.sqlite")) as tm:
        file_path = tmp_path / "sample.txt"
        await asyncio.to_thread(file_path.write_text, "hello\n")
        result = await tm.file_read(str(file_path))
        assert "content" in result and result["content"] == "hello\n"
        await tm.file_append_text(str(file_path), "world\n")
        result = await tm.file_read(str(file_path))
        assert result["content"] == "hello\nworld\n"

@pytest.mark.asyncio
async def test_shell_exec_and_wait():
    async with ToolManager(db_path=":memory:") as tm:
        session_id = "test"
        await tm.shell_exec("echo hello", session_id)
        result = await tm.shell_wait(session_id)
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]


@pytest.mark.asyncio

async def test_media_generate_speech(tmp_path, monkeypatch):
    tm = ToolManager(db_path=":memory:")
    out_file = tmp_path / "speech.mp3"

    class DummyTTS:
        def __init__(self, text):
            self.text = text

        def save(self, path):
            with open(path, "wb") as f:
                f.write(b"data")

    monkeypatch.setattr("gtts.gTTS", DummyTTS)
    result = await tm.media_generate_speech("hello", str(out_file))
    assert "error" in result


@pytest.mark.asyncio
async def test_info_search_image(monkeypatch):
    tm = ToolManager(db_path=":memory:")

    class MockResp:
        async def json(self):
            return {
                "results": [
                    {
                        "id": "1",
                        "alt_description": "cat",
                        "urls": {"small": "http://example.com/cat.jpg"},
                    }
                ]
            }

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    class MockSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        def get(self, url):
            return MockResp()

    monkeypatch.setattr("aiohttp.ClientSession", lambda: MockSession())
    result = await tm.info_search_image("cat")
    assert result["results"][0]["url"] == "http://example.com/cat.jpg"


@pytest.mark.asyncio
async def test_media_analyze_video(monkeypatch):
    tm = ToolManager(db_path=":memory:")

    class DummyCap:
        def __init__(self, path):
            self.path = path

        def isOpened(self):
            return True

        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 10
            if prop == cv2.CAP_PROP_FPS:
                return 5.0
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 640
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 480
            return 0

        def release(self):
            pass

    monkeypatch.setattr("cv2.VideoCapture", lambda path: DummyCap(path))
    result = await tm.media_analyze_video("dummy.mp4")
    assert result["frames"] == 10
    assert result["duration"] == 2.0



@pytest.mark.asyncio
async def test_disallowed_path(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    tm = ToolManager(db_path=os.path.join(root, "db.sqlite"), root_dir=str(root))
    outside = tmp_path / "outside.txt"
    await asyncio.to_thread(outside.write_text, "secret")
    result = await tm.file_read(str(outside))
    assert "error" in result


@pytest.mark.asyncio
async def test_file_read_not_found(tmp_path):
    tm = ToolManager(db_path=os.path.join(tmp_path, "db.sqlite"))
    result = await tm.file_read(str(tmp_path / "missing.txt"))
    assert "error" in result


@pytest.mark.asyncio
async def test_shell_wait_no_session(caplog):
    tm = ToolManager(db_path=":memory:")
    with caplog.at_level(logging.ERROR):
        result = await tm.shell_wait("bad")
    assert any("shell_wait" in r.getMessage() for r in caplog.records)
    assert "error" in result


@pytest.mark.asyncio
async def test_media_analyze_image(monkeypatch):
    tm = ToolManager(db_path=":memory:")

    import types
    import sys
    pytesseract = types.SimpleNamespace(image_to_string=lambda img: "text")
    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract)
    monkeypatch.setattr("PIL.Image.open", lambda p: "img")

    result = await tm.media_analyze_image("img.png")
    assert result["text"] == "text"


@pytest.mark.asyncio
async def test_media_recognize_speech(monkeypatch):
    tm = ToolManager(db_path=":memory:")

    import types
    import sys

    class DummyAudioFile:
        def __init__(self, path):
            self.path = path
        def __enter__(self):
            return "src"
        def __exit__(self, exc_type, exc, tb):
            pass

    class DummyRecognizer:
        def record(self, source):
            return b"aud"
        def recognize_sphinx(self, audio):
            return "hello"

    speech_mod = types.SimpleNamespace(AudioFile=DummyAudioFile, Recognizer=DummyRecognizer)
    monkeypatch.setitem(sys.modules, "speech_recognition", speech_mod)

    result = await tm.media_recognize_speech("sound.wav")
    assert result["text"] == "hello"


@pytest.mark.asyncio
async def test_media_describe_video(monkeypatch):
    tm = ToolManager(db_path=":memory:")

    class DummyFrame:
        def mean(self, axis=None):
            return [1.0, 2.0, 3.0]

    class DummyCap:
        def __init__(self, path):
            self.path = path
        def isOpened(self):
            return True
        def read(self):
            return True, DummyFrame()
        def release(self):
            pass

    import types
    import sys
    cv2_mod = types.SimpleNamespace(VideoCapture=lambda path: DummyCap(path))
    monkeypatch.setitem(sys.modules, "cv2", cv2_mod)

    result = await tm.media_describe_video("video.mp4")
    assert result["avg_color"] == [1.0, 2.0, 3.0]

