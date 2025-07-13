import os

os.environ.setdefault("OPENAI_API_KEY", "test")

import pytest

@pytest.fixture(autouse=True, scope="session")
def _set_openai_key():
    """Ensure OPENAI_API_KEY is available for tests."""
    os.environ.setdefault("OPENAI_API_KEY", "test")
