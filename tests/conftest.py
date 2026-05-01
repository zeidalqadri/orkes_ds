"""Test configuration and fixtures for the Opencode bot core."""
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_core_path = Path.home() / ".opencode-bot"
if str(_core_path) not in sys.path:
    sys.path.insert(0, str(_core_path))


@pytest.fixture(autouse=True)
def reset_state():
    """Reset thread-level state globals between tests."""
    from core import state
    state._shutdown = threading.Event()
    state._agent_wake = threading.Event()
    state._child_procs = set()
    state._token_usage = {"input": 0, "output": 0}
    state._step_count = 0
    state._goal_step_count = 0
    state._opencode_semaphore = threading.Semaphore(2)
    state.PERMISSION_MODE = "act"
    state.FILE_CACHE.clear()
    state.ctx_budget_reset()
    state._ctx_summaries = []
    state._log_fh = None
    state._ctx_chars = 0
    state._ctx_stack = []
    state._expert_registry = {}
    state._local_experts = {}
    state.handling_message = threading.Event()
    import core.loops
    core.loops._last_chat_wake_check = 0.0
    core.loops._last_seeded_goal_hash = ""
    core.loops._last_chat_wake_seed = 0.0
    core.loops._last_handled_message_ts = 0.0
    core.loops._last_handled_message_text = ""
    yield


@pytest.fixture
def mock_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory with standard structure."""
    proj = tmp_path / "test_project"
    proj.mkdir()
    (proj / "context").mkdir()
    return proj


@pytest.fixture
def init_state(mock_project_dir: Path):
    """Initialize engine path/config on state module using tmp_path."""
    from core import state
    from core.engine import _init_paths, _init_config, _init_permission

    _init_paths(mock_project_dir)
    _init_config()
    _init_permission()
    return state


@pytest.fixture
def mock_telegram():
    """Mock all Telegram HTTP calls so tests don't hit the network."""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True, "result": {"message_id": 12345}
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def sample_goals() -> dict:
    return {
        "active": "Build the new feature X",
        "done_short": "task complete",
        "done_marker": "(done)",
        "empty": "",
        "idle": "no active task",
        "url": "https://github.com/owner/repo/issues/42",
    }


@pytest.fixture
def sample_state_text() -> str:
    return (
        "# Arbos State\n"
        "Updated: 2026-04-28T15:00 UTC\n\n"
        "## Status: IDLE — completed after 3 steps\n\n"
        "## Last Completed: Build feature X\n"
    )


@pytest.fixture
def garbled_state_text() -> str:
    return (
        "# Arbos State\n"
        "Updated: 2026-04-28T15:00 UTC\n"
        "Okay so I think the issue is in the for loop... Let me check the imports..."
        "## Status: IDLE — completed after 3 steps\n\n"
        "## Last Completed: Build feature X\n"
        "Let me verify this by running ruff... Yes, that looks correct."
    )
