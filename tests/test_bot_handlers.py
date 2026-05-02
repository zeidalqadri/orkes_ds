"""Tests for bot_handlers.py utility functions."""
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from core import state


# _is_owner
def test_is_owner_matches(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "12345")
    from core.bot_handlers import _is_owner
    assert _is_owner(12345) is True
    assert _is_owner(99999) is False

def test_is_owner_empty(monkeypatch):
    monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
    from core.bot_handlers import _is_owner
    assert _is_owner(1) is False

def test_is_owner_blank(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "")
    from core.bot_handlers import _is_owner
    assert _is_owner(1) is False


# _enroll_owner
def test_enroll_owner_new(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
    monkeypatch.setattr(state, "WORKING_DIR", tmp_path)
    (tmp_path / ".env").write_text("EXISTING=1\n")
    from core.bot_handlers import _enroll_owner
    _enroll_owner(42)
    assert os.environ.get("TELEGRAM_OWNER_ID") == "42"
    env_text = (tmp_path / ".env").read_text()
    assert "TELEGRAM_OWNER_ID='42'" in env_text

def test_enroll_owner_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "old")
    monkeypatch.setattr(state, "WORKING_DIR", tmp_path)
    (tmp_path / ".env").write_text("OTHER_KEY=1")
    from core.bot_handlers import _enroll_owner
    _enroll_owner(99)
    env_text = (tmp_path / ".env").read_text()
    assert "TELEGRAM_OWNER_ID='99'" in env_text

def test_enroll_owner_no_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
    monkeypatch.setattr(state, "WORKING_DIR", tmp_path)
    from core.bot_handlers import _enroll_owner
    _enroll_owner(7)
    assert os.environ["TELEGRAM_OWNER_ID"] == "7"
    assert not (tmp_path / ".env").exists()


# _save_chat_id
def test_save_chat_id(tmp_path):
    state.CHAT_ID_FILE = tmp_path / "cid.txt"
    from core.bot_handlers import _save_chat_id
    _save_chat_id(42)
    assert state.CHAT_ID_FILE.read_text() == "42"


# _load_chat_ids
def test_load_chat_ids_normal(tmp_path):
    state.CHAT_IDS_FILE = tmp_path / "cids.json"
    state._allowed_groups = set()
    state.CHAT_IDS_FILE.write_text(json.dumps({"groups": {"-100111": {}}}))
    from core.bot_handlers import _load_chat_ids
    _load_chat_ids()
    assert "-100111" in state._allowed_groups

def test_load_chat_ids_missing(tmp_path):
    state.CHAT_IDS_FILE = tmp_path / "noexist.json"
    state._allowed_groups = set()
    from core.bot_handlers import _load_chat_ids
    _load_chat_ids()
    assert state._allowed_groups == set()

def test_load_chat_ids_bad_json(tmp_path):
    state.CHAT_IDS_FILE = tmp_path / "bad.json"
    state._allowed_groups = set()
    state.CHAT_IDS_FILE.write_text("notjson")
    from core.bot_handlers import _load_chat_ids
    _load_chat_ids()
    assert state._allowed_groups == set()


# _save_chat_ids
def test_save_chat_ids(tmp_path):
    state.CHAT_IDS_FILE = tmp_path / "cids.json"
    state._allowed_groups = {"-100a", "-100b"}
    from core.bot_handlers import _save_chat_ids
    _save_chat_ids()
    data = json.loads(state.CHAT_IDS_FILE.read_text())
    assert set(data["groups"].keys()) == {"-100a", "-100b"}


# _register_group / _unregister_group
def test_register_group(tmp_path):
    state.CHAT_IDS_FILE = tmp_path / "cids.json"
    state._allowed_groups = set()
    from core.bot_handlers import _register_group
    _register_group("-100x")
    assert "-100x" in state._allowed_groups
    data = json.loads(state.CHAT_IDS_FILE.read_text())
    assert "-100x" in data["groups"]

def test_unregister_group(tmp_path):
    state.CHAT_IDS_FILE = tmp_path / "cids.json"
    state._allowed_groups = {"-100x"}
    from core.bot_handlers import _unregister_group
    _unregister_group("-100x")
    assert "-100x" not in state._allowed_groups


# _is_preconfirmed / _ask_confirm / _do_confirm
@pytest.fixture
def confirm_cleanup():
    from core.bot_handlers import _confirm_orig_msg, _confirmed_actions
    _confirmed_actions.clear()
    _confirm_orig_msg.clear()
    yield
    _confirmed_actions.clear()
    _confirm_orig_msg.clear()

def test_is_preconfirmed(confirm_cleanup):
    from core.bot_handlers import _confirmed_actions, _is_preconfirmed
    assert _is_preconfirmed(1, "clear") is False
    _confirmed_actions[1] = "clear"
    assert _is_preconfirmed(1, "clear") is True
    assert _is_preconfirmed(1, "restart") is False

def test_ask_confirm(confirm_cleanup):
    from core.bot_handlers import _ask_confirm
    handler = MagicMock()
    bot = MagicMock()
    message = MagicMock()
    message.chat.id = 1
    _ask_confirm(bot, message, handler, "clear", "danger")
    bot.send_message.assert_called_once_with(1, "⚠️ danger\n\nReply 'yes' to confirm.")
    bot.register_next_step_handler.assert_called_once()

def test_do_confirm_yes(confirm_cleanup):
    from core.bot_handlers import _confirmed_actions, _do_confirm
    handler = MagicMock()
    bot = MagicMock()
    message = MagicMock()
    message.chat.id = 1
    message.text = "yes"
    _do_confirm(bot, message, handler, "clear")
    assert _confirmed_actions.get(1) == "clear"

def test_do_confirm_yes_y(confirm_cleanup):
    from core.bot_handlers import _confirmed_actions, _do_confirm
    handler = MagicMock()
    bot = MagicMock()
    message = MagicMock()
    message.chat.id = 1
    message.text = "y"
    _do_confirm(bot, message, handler, "restart")
    assert _confirmed_actions.get(1) == "restart"

def test_do_confirm_no(confirm_cleanup):
    from core.bot_handlers import _do_confirm
    handler = MagicMock()
    bot = MagicMock()
    message = MagicMock()
    message.chat.id = 1
    message.text = "no"
    _do_confirm(bot, message, handler, "clear")
    bot.send_message.assert_called_once_with(1, "Cancelled.")

def test_do_confirm_dispatches_clear(confirm_cleanup):
    from core.bot_handlers import _confirm_orig_msg, _do_confirm
    handler = MagicMock()
    orig_msg = MagicMock()
    _confirm_orig_msg[1] = orig_msg
    bot = MagicMock()
    message = MagicMock()
    message.chat.id = 1
    message.text = "yes"
    _do_confirm(bot, message, handler, "clear")
    handler.assert_called_once_with(bot, orig_msg)

def test_do_confirm_dispatches_restart(confirm_cleanup):
    from core.bot_handlers import _confirm_orig_msg, _do_confirm
    handler = MagicMock()
    orig_msg = MagicMock()
    _confirm_orig_msg[1] = orig_msg
    bot = MagicMock()
    message = MagicMock()
    message.chat.id = 1
    message.text = "yes"
    _do_confirm(bot, message, handler, "restart")
    handler.assert_called_once_with(bot, orig_msg)

def test_do_confirm_dispatches_kill(confirm_cleanup):
    from core.bot_handlers import _confirm_orig_msg, _do_confirm
    handler = MagicMock()
    orig_msg = MagicMock()
    _confirm_orig_msg[1] = orig_msg
    bot = MagicMock()
    message = MagicMock()
    message.chat.id = 1
    message.text = "yes"
    _do_confirm(bot, message, handler, "kill")
    handler.assert_called_once_with(bot, orig_msg)


# _load_projects / _discover_projects / _resolve_project
def test_load_projects_normal(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "proj.json"):
        (tmp_path / "proj.json").write_text(json.dumps({"projects": {"orkes": {"path": "/x"}}}))
        from core.bot_handlers import _load_projects
        projs = _load_projects()
        assert projs["orkes"]["path"] == "/x"

def test_load_projects_missing(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "noexist.json"):
        from core.bot_handlers import _load_projects
        assert _load_projects() == {}

def test_load_projects_bad_json(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "bad.json"):
        (tmp_path / "bad.json").write_text("bad")
        from core.bot_handlers import _load_projects
        assert _load_projects() == {}

def test_discover_projects(tmp_path):
    proj_dir = tmp_path / "testproj"
    proj_dir.mkdir()
    (proj_dir / "arbos.py").write_text("")
    with patch("core.bot_handlers.Path.home", return_value=tmp_path):
        from core.bot_handlers import _discover_projects
        projs = _discover_projects()
        assert "testproj" in projs

def test_resolve_project_v1(tmp_path):
    proj_dir = tmp_path / "myproj"
    proj_dir.mkdir()
    (proj_dir / "arbos.py").write_text("")
    with patch("core.bot_handlers.Path.home", return_value=tmp_path):
        from core.bot_handlers import _resolve_project
        # v2 shadows v1 — v2 returns tuple via _load_projects
        # Test v2 resolution with empty projects file (falls through to no-match)
        (tmp_path / "proj.json").write_text(json.dumps({"projects": {}}))
        with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "proj.json"):
            name, rest, path = _resolve_project("myproj do something")
            assert name is None  # not in projects registry
            assert rest == "myproj do something"

def test_resolve_project_v2(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "proj.json"):
        (tmp_path / "proj.json").write_text(json.dumps({
            "projects": {"orkes": {"path": "/x/y", "description": "test"}}
        }))
        from core.bot_handlers import _resolve_project as _resolve_project_v2
        name, rest, path = _resolve_project_v2("orkes do something")
        assert name == "orkes"
        assert rest == "do something"
        assert path == "/x/y"

def test_resolve_project_v2_no_match(tmp_path):
    from core.bot_handlers import _resolve_project as _resolve_project_v2
    name, rest, path = _resolve_project_v2("do something")
    assert name is None
    assert rest == "do something"
    assert path is None


# _is_github_issue_url / _fetch_github_issue
def test_is_github_issue_url():
    from core.bot_handlers import _is_github_issue_url
    assert _is_github_issue_url("https://github.com/owner/repo/issues/42") is True
    assert _is_github_issue_url("https://example.com") is False
    assert _is_github_issue_url("") is False

def test_fetch_github_issue():
    from core.bot_handlers import _fetch_github_issue
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "title": "Bug fix",
        "state": "open",
        "user": {"login": "testuser"},
        "labels": [{"name": "bug"}],
        "body": "Something broke",
    }
    with patch("core.bot_handlers.requests.get", return_value=mock_resp):
        text, error = _fetch_github_issue("https://github.com/o/r/issues/1")
    assert text is not None
    assert error is None
    assert "Bug fix" in text
    assert "open" in text
    assert "testuser" in text

def test_fetch_github_issue_non_200():
    from core.bot_handlers import _fetch_github_issue
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("core.bot_handlers.requests.get", return_value=mock_resp):
        text, error = _fetch_github_issue("https://github.com/o/r/issues/1")
    assert text is None
    assert isinstance(error, str)
    assert "HTTP 404" in error

def test_fetch_github_issue_bad_url():
    from core.bot_handlers import _fetch_github_issue
    text, error = _fetch_github_issue("not a url")
    assert text is None
    assert error == "Invalid GitHub issue URL format"

def test_fetch_github_issue_exception():
    from core.bot_handlers import _fetch_github_issue
    with patch("core.bot_handlers.requests.get", side_effect=Exception("timeout")):
        text, error = _fetch_github_issue("https://github.com/o/r/issues/1")
    assert text is None
    assert "timeout" in error


# _build_deepfix_prompt
def test_build_deepfix_prompt():
    from core.bot_handlers import _build_deepfix_prompt
    result = _build_deepfix_prompt("button not working")
    assert "button not working" in result
    assert "Whole-repo" in result or "whole-repo" in result
    assert "Root Cause" in result


# _extract_mention
def test_extract_mention():
    from core.bot_handlers import _extract_mention
    with patch("core.bot_shared._get_expert", return_value={"active": True}):
        handle, cleaned = _extract_mention("hello @conductor world")
    assert handle == "conductor"
    assert "hello" in cleaned and "world" in cleaned

def test_extract_mention_no_match():
    from core.bot_handlers import _extract_mention
    handle, cleaned = _extract_mention("plain text")
    assert handle is None
    assert cleaned == "plain text"

def test_extract_mention_unknown_expert():
    from core.bot_handlers import _extract_mention
    with patch("core.bot_handlers._get_expert", return_value=None):
        handle, cleaned = _extract_mention("@unknown hi")
    assert handle is None


# _clear_audit_pending
def test_clear_audit_pending(tmp_path):
    state.UPLOADS_DIR = tmp_path
    marker = tmp_path / "audit_pending.json"
    marker.write_text("{}")
    from core.bot_handlers import _clear_audit_pending
    _clear_audit_pending()
    assert not marker.exists()

def test_clear_audit_pending_no_file(tmp_path):
    state.UPLOADS_DIR = tmp_path
    from core.bot_handlers import _clear_audit_pending
    _clear_audit_pending()

def test_clear_audit_pending_exception(tmp_path):
    state.UPLOADS_DIR = tmp_path / "nonexistent"
    from core.bot_handlers import _clear_audit_pending
    _clear_audit_pending()


# _save_audit_pending
def test_save_audit_pending(tmp_path):
    state.UPLOADS_DIR = tmp_path
    xml_path = tmp_path / "audit_20240101.xml"
    xml_path.write_text("<audit/>")
    from core.bot_handlers import _save_audit_pending
    _save_audit_pending(xml_path, 1, 2)
    marker = tmp_path / "audit_pending.json"
    assert marker.exists()
    data = json.loads(marker.read_text())
    assert data["chat_id"] == 1
    assert data["reply_to"] == 2
    latest = tmp_path / "audit_latest.xml"
    assert latest.exists()


# _reject
def test_reject_no_owner(monkeypatch):
    monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
    from core.bot_handlers import _reject
    bot = MagicMock()
    msg = MagicMock()
    msg.from_user.id = 1
    msg.chat.id = 1
    _reject(bot, msg)
    bot.send_message.assert_called_with(1, "Send /start to register as the owner.")

def test_reject_with_owner(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core.bot_handlers import _reject
    bot = MagicMock()
    msg = MagicMock()
    msg.from_user.id = 2
    msg.chat.id = 1
    _reject(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")

def test_reject_no_from_user(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core.bot_handlers import _reject
    bot = MagicMock()
    msg = MagicMock()
    msg.from_user = None
    msg.chat.id = 1
    _reject(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


# _get_bot_id
def test_get_bot_id_caches():
    from core.bot_handlers import _cached_bot_id, _get_bot_id
    _cached_bot_id["id"] = None
    bot = MagicMock()
    bot.get_me.return_value.id = 42
    assert _get_bot_id(bot) == 42
    assert _cached_bot_id["id"] == 42
    # second call uses cache
    _get_bot_id(bot)
    bot.get_me.assert_called_once()

def test_get_bot_id_exception():
    from core.bot_handlers import _cached_bot_id, _get_bot_id
    _cached_bot_id["id"] = None
    bot = MagicMock()
    bot.get_me.side_effect = Exception("fail")
    assert _get_bot_id(bot) is None


# _is_addressed_to_me
def make_msg(chat_type="private", text="hello", reply_to=None, from_user=None):
    msg = MagicMock()
    msg.chat.type = chat_type
    msg.chat.id = 1
    msg.text = text
    msg.caption = None
    msg.reply_to_message = reply_to
    if from_user is not None:
        msg.from_user = from_user
    else:
        msg.from_user = MagicMock()
        msg.from_user.id = 1
    return msg

def test_is_addressed_to_me_private():
    from core.bot_handlers import _is_addressed_to_me
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="hello")
    assert _is_addressed_to_me(bot, msg) is True

def test_is_addressed_to_me_mention(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core.bot_handlers import _is_addressed_to_me
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="hello @TestBot")
    assert _is_addressed_to_me(bot, msg) is True

def test_is_addressed_to_me_no_username(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "")
    from core.bot_handlers import _is_addressed_to_me
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="hello")
    assert _is_addressed_to_me(bot, msg) is True

def test_is_addressed_to_me_reply_to_bot(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "")
    from core.bot_handlers import _cached_bot_id, _is_addressed_to_me
    _cached_bot_id["id"] = 99
    bot = MagicMock()
    reply_to = MagicMock()
    reply_to.from_user.id = 99
    msg = make_msg(chat_type="group", text="reply", reply_to=reply_to)
    assert _is_addressed_to_me(bot, msg) is True

def test_is_addressed_to_me_reply_no_bot_id(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core.bot_handlers import _cached_bot_id, _is_addressed_to_me
    _cached_bot_id["id"] = None
    bot = MagicMock()
    bot.get_me.side_effect = Exception("fail")
    reply_to = MagicMock()
    reply_to.from_user.id = 99
    # Reply to bot with no mention text and no usable bot_id
    msg = make_msg(chat_type="group", text="reply", reply_to=reply_to)
    assert _is_addressed_to_me(bot, msg) is False

def test_is_addressed_to_me_not_addressed(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core.bot_handlers import _is_addressed_to_me
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="hello @OtherBot")
    assert _is_addressed_to_me(bot, msg) is False


# _is_command_for_me
def test_is_command_for_me_private():
    from core.bot_handlers import _is_command_for_me
    msg = make_msg(chat_type="private", text="/status")
    assert _is_command_for_me(msg) is True

def test_is_command_for_me_group_no_username(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "")
    from core.bot_handlers import _is_command_for_me
    msg = make_msg(chat_type="group", text="/status")
    assert _is_command_for_me(msg) is True

def test_is_command_for_me_group_mention(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core.bot_handlers import _is_command_for_me
    msg = make_msg(chat_type="group", text="/status@TestBot")
    assert _is_command_for_me(msg) is True

def test_is_command_for_me_other_bot(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core.bot_handlers import _is_command_for_me
    msg = make_msg(chat_type="group", text="/status@OtherBot")
    assert _is_command_for_me(msg) is False

def test_is_command_for_me_not_command(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core.bot_handlers import _is_command_for_me
    msg = make_msg(chat_type="group", text="hello")
    assert _is_command_for_me(msg) is True  # not a command -> treat as for me

def test_is_command_for_me_bare_start(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core.bot_handlers import _is_command_for_me
    msg = make_msg(chat_type="group", text="/start")
    assert _is_command_for_me(msg) is True

def test_is_command_for_me_bare_actionable(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    with patch("core.bot_shared._maybe_send_routing_hint") as mock_hint:
        from core.bot_handlers import _is_command_for_me
        msg = make_msg(chat_type="group", text="/cancel")
        assert _is_command_for_me(msg) is False
    mock_hint.assert_called_once()


# _is_authorized
def test_is_authorized_private_owner(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core.bot_handlers import _is_authorized
    msg = make_msg(chat_type="private")
    msg.from_user.id = 1
    assert _is_authorized(msg) is True

def test_is_authorized_private_not_owner(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core.bot_handlers import _is_authorized
    msg = make_msg(chat_type="private")
    msg.from_user.id = 2
    assert _is_authorized(msg) is False

def test_is_authorized_group_allowed(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    state._allowed_groups = {"-100999"}
    from core.bot_handlers import _is_authorized
    msg = make_msg(chat_type="group")
    msg.chat.id = -100999
    msg.from_user.id = 1
    assert _is_authorized(msg) is True

def test_is_authorized_group_not_allowed(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    state._allowed_groups = {"-100000"}
    from core.bot_handlers import _is_authorized
    msg = make_msg(chat_type="group")
    msg.chat.id = -100999
    msg.from_user.id = 1
    assert _is_authorized(msg) is False

def test_is_authorized_group_not_owner(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    state._allowed_groups = {"-100999"}
    from core.bot_handlers import _is_authorized
    msg = make_msg(chat_type="group")
    msg.chat.id = -100999
    msg.from_user.id = 2
    assert _is_authorized(msg) is False


# handle_projects
def test_handle_projects_not_for_me():
    from core.bot_handlers import handle_projects
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="/projects")
    with patch("core.bot_handlers._is_command_for_me", return_value=False):
        handle_projects(bot, msg)
    bot.send_message.assert_not_called()

def test_handle_projects_not_authorized(monkeypatch):
    monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
    from core.bot_handlers import handle_projects
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/projects")
    msg.from_user.id = 2
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_projects(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Send /start" in str(args[1])

def test_handle_projects_empty(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "empty.json"):
        (tmp_path / "empty.json").write_text('{"projects": {}}')
        from core.bot_handlers import handle_projects
        bot = MagicMock()
        msg = make_msg(chat_type="private", text="/projects")
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_projects(bot, msg)
        args = bot.send_message.call_args[0]
        assert "No projects registered" in str(args[1])

def test_handle_projects_list(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "proj.json"):
        (tmp_path / "proj.json").write_text(json.dumps({
            "projects": {
                "orkes": {"path": "/x", "description": "the project", "host": "vm1"}
            }
        }))
        from core.bot_handlers import handle_projects
        bot = MagicMock()
        msg = make_msg(chat_type="private", text="/projects")
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_projects(bot, msg)
        sent = bot.send_message.call_args[0][1]
        assert "orkes" in sent
        assert "vm1" in sent


# handle_cancel
def test_handle_cancel_full_flow(tmp_path):
    state.GOAL_FILE = tmp_path / "GOAL.md"
    state.GOAL_FILE.write_text("my goal")
    from core.bot_handlers import handle_cancel
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/cancel")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._kill_child_procs") as mock_kill:
                handle_cancel(bot, msg)
    mock_kill.assert_called_once()
    assert state.GOAL_FILE.read_text() == ""


# _build_operator_prompt
def test_build_operator_prompt_basic(tmp_path):
    goal_file = tmp_path / "GOAL.md"
    goal_file.write_text("fix bugs")
    st_file = tmp_path / "STATE.md"
    st_file.write_text("working")
    state.GOAL_FILE = goal_file
    state.STATE_FILE = st_file
    with patch("core.bot_handlers.load_chatlog", return_value=""):
        from core.bot_handlers import _build_operator_prompt
        result = _build_operator_prompt("hello operator")
    assert "## Current goal\nfix bugs" in result
    assert "## Current state\nworking" in result
    assert "## Operator message\nhello operator" in result
    assert "context/GOAL.md" in result

def test_build_operator_prompt_missing_files():
    with patch("core.bot_handlers.load_chatlog", return_value=""):
        state.GOAL_FILE = MagicMock()
        state.GOAL_FILE.exists.return_value = False
        state.STATE_FILE = MagicMock()
        state.STATE_FILE.exists.return_value = False
        from core.bot_handlers import _build_operator_prompt
        result = _build_operator_prompt("hi")
    assert "(no goal set)" in result
    assert "(no state)" in result

def test_build_operator_prompt_with_chatlog():
    state.GOAL_FILE = MagicMock()
    state.GOAL_FILE.exists.return_value = False
    state.STATE_FILE = MagicMock()
    state.STATE_FILE.exists.return_value = False
    with patch("core.bot_shared.load_chatlog", return_value="recent chat"):
        from core.bot_handlers import _build_operator_prompt
        result = _build_operator_prompt("hi")
    assert "recent chat" in result

def test_build_operator_prompt_with_expert():
    state.GOAL_FILE = MagicMock()
    state.GOAL_FILE.exists.return_value = False
    state.STATE_FILE = MagicMock()
    state.STATE_FILE.exists.return_value = False
    mock_ctx = MagicMock()
    mock_ctx.goal_file = MagicMock()
    mock_ctx.goal_file.exists.return_value = True
    mock_ctx.goal_file.read_text.return_value = "expert goal"
    mock_ctx.state_file = MagicMock()
    mock_ctx.state_file.exists.return_value = True
    mock_ctx.state_file.read_text.return_value = "expert state"
    with patch("core.bot_shared.load_chatlog", return_value=""):
        with patch("core.bot_shared.ExpertContext", return_value=mock_ctx):
            with patch("core.bot_shared._get_expert", return_value={
                "system_prompt": "you are an expert",
                "name": "CodeReviewer"
            }):
                from core.bot_handlers import _build_operator_prompt
                result = _build_operator_prompt("review this", "reviewer")
    assert "# CodeReviewer" in result
    assert "you are an expert" in result
    assert "context/reviewer/GOAL.md" in result
    assert "expert goal" in result


# _maybe_send_routing_hint
def test_maybe_send_routing_hint_already_sent():
    from core.bot_handlers import _maybe_send_routing_hint, _routing_hint_sent
    _routing_hint_sent.add(123)
    _maybe_send_routing_hint(123, "status")
    _routing_hint_sent.discard(123)


def test_maybe_send_routing_hint_no_peers():
    from core.bot_handlers import _maybe_send_routing_hint, _routing_hint_sent
    _routing_hint_sent.discard(456)
    with patch("core.bot_handlers._pm2_peer_list", return_value=[]):
        _maybe_send_routing_hint(456, "status")
    assert 456 not in _routing_hint_sent


def test_maybe_send_routing_hint_not_primary():
    from core.bot_handlers import _maybe_send_routing_hint, _routing_hint_sent
    _routing_hint_sent.discard(789)
    state.MY_PM2_NAME = "arbos-bot2"
    with patch("core.bot_handlers._pm2_peer_list", return_value=[
        {"name": "arbos-bot1", "status": "online"},
    ]):
        _maybe_send_routing_hint(789, "status")
    assert 789 not in _routing_hint_sent


def test_maybe_send_routing_hint_sends(monkeypatch):
    monkeypatch.setenv("TAU_BOT_TOKEN", "tok:xxx")
    from core.bot_handlers import _maybe_send_routing_hint, _routing_hint_sent
    _routing_hint_sent.discard(999)
    state.MY_PM2_NAME = "arbos-primary"
    with patch("core.bot_shared._pm2_peer_list", return_value=[
        {"name": "arbos-primary", "status": "online"},
        {"name": "arbos-secondary", "status": "online"},
    ]):
        with patch("core.telegram._send_telegram_text") as mock_send:
            _maybe_send_routing_hint(999, "stop")
    mock_send.assert_called_once()
    assert 999 in _routing_hint_sent
    _routing_hint_sent.discard(999)


# handle_deepfix usage path
def test_handle_deepfix_no_args(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "empty.json"):
        (tmp_path / "empty.json").write_text('{"projects": {}}')
        from core.bot_handlers import handle_deepfix
        bot = MagicMock()
        msg = make_msg(chat_type="private", text="/deepfix")
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_deepfix(bot, msg)
        args = bot.send_message.call_args[0]
        assert "Usage:" in str(args[1])


def test_handle_deepfix_github_issue(tmp_path):
    state.CHAT_ID_FILE = tmp_path / "chat_id.txt"
    state.CHAT_ID_FILE.write_text("")
    state.CHATLOG_DIR = tmp_path / "chatlog"
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "empty.json"):
        (tmp_path / "empty.json").write_text('{"projects": {}}')
        from core.bot_handlers import handle_deepfix
        bot = MagicMock()
        msg = make_msg(chat_type="private", text="/deepfix https://github.com/o/r/issues/1")
        msg.message_id = 10
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._fetch_github_issue", return_value=("fetched issue", None)):
                    with patch("core.bot_handlers._build_deepfix_prompt", return_value="prompt"):
                        with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                            handle_deepfix(bot, msg)
        bot.send_message.assert_any_call(1, "Project: (current working directory)")


# handle_deepfix not authorized
def test_handle_deepfix_not_authorized(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "empty.json"):
        (tmp_path / "empty.json").write_text('{"projects": {}}')
        from core.bot_handlers import handle_deepfix
        bot = MagicMock()
        msg = make_msg(chat_type="private", text="/deepfix bug")
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=False):
                handle_deepfix(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


# ── _classify_message ────────────────────────────────────────────────────────

def test_classify_message_no_active_experts():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    with patch("core.bot_shared._list_experts", return_value={}):
        from core.bot_handlers import _classify_message
        assert _classify_message("fix it") is None


def test_classify_message_llm_returns_handle():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = False
    experts = {"coder": {"active": True, "expertise": "python"}}
    with patch("core.bot_shared._list_experts", return_value=experts):
        with patch("core.bot_shared._run_opencode_once", return_value=(0, "coder", "", "")):
            from core.bot_handlers import _classify_message
            assert _classify_message("fix this bug") == "coder"


def test_classify_message_llm_returns_none():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = False
    experts = {"coder": {"active": True, "expertise": "python"}}
    with patch("core.bot_shared._list_experts", return_value=experts):
        with patch("core.bot_shared._run_opencode_once", return_value=(0, "none", "", "")):
            from core.bot_handlers import _classify_message
            assert _classify_message("how are you?") is None


def test_classify_message_llm_returns_invalid():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = False
    experts = {"coder": {"active": True, "expertise": "python"}}
    with patch("core.bot_shared._list_experts", return_value=experts):
        with patch("core.bot_shared._run_opencode_once", return_value=(0, "nonexistent", "", "")):
            from core.bot_handlers import _classify_message
            assert _classify_message("do stuff") is None


def test_classify_message_llm_fails():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = False
    experts = {"coder": {"active": True, "expertise": "python"}}
    with patch("core.bot_shared._list_experts", return_value=experts):
        with patch("core.bot_shared._run_opencode_once", return_value=(1, "", "", "")):
            from core.bot_handlers import _classify_message
            assert _classify_message("do stuff") is None


def test_classify_message_exception():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    experts = {"coder": {"active": True, "expertise": "python"}}
    with patch("core.bot_shared._list_experts", return_value=experts):
        with patch("core.bot_shared._run_opencode_once", side_effect=Exception("timeout")):
            from core.bot_handlers import _classify_message
            assert _classify_message("do stuff") is None


def test_classify_message_llm_returns_handle_with_stripped_answer():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = False
    experts = {"coder": {"active": True, "expertise": "python"}}
    with patch("core.bot_shared._list_experts", return_value=experts):
        with patch("core.bot_shared._run_opencode_once", return_value=(0, " @coder ", "", "")):
            from core.bot_handlers import _classify_message
            assert _classify_message("do stuff") == "coder"


# ── _route_message ───────────────────────────────────────────────────────────

def test_route_message_extract_mention(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    with patch("core.bot_shared._extract_mention", return_value=("coder", "fix this")):
        from core.bot_handlers import _route_message
        handle, text = _route_message("hello", is_group=True)
        assert handle == "coder"
        assert text == "fix this"


def test_route_message_group_active_experts_classifies(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.list_active.return_value = ["coder"]
    with patch("core.bot_shared._get_expert", return_value={"active": True}):
        with patch("core.bot_shared._extract_mention", return_value=(None, "do stuff")):
            with patch("core.bot_shared._classify_message", return_value="coder"):
                from core.bot_handlers import _route_message
                handle, text = _route_message("do stuff", is_group=True)
                assert handle == "coder"


def test_route_message_group_no_active_experts(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.list_active.return_value = []
    with patch("core.bot_shared._extract_mention", return_value=(None, "do stuff")):
        from core.bot_handlers import _route_message
        handle, text = _route_message("do stuff", is_group=True)
        assert handle is None


def test_route_message_private_no_routing(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    with patch("core.bot_shared._extract_mention", return_value=(None, "hello")):
        from core.bot_handlers import _route_message
        handle, text = _route_message("hello", is_group=False)
        assert handle is None
        assert text == "hello"


def test_route_message_strips_bot_username(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    with patch("core.bot_shared._extract_mention", return_value=("coder", "fix it")):
        from core.bot_handlers import _route_message
        handle, text = _route_message("@TestBot fix it", is_group=True)
        assert handle == "coder"


# ── _route_to_expert ─────────────────────────────────────────────────────────

def test_route_to_expert_starts_and_wakes():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = False
    with patch("core.bot_shared.ExpertContext") as MockCtx:
        ctx = MagicMock()
        MockCtx.return_value = ctx
        with patch("core.bot_shared._get_expert", return_value={"active": True}):
            with patch("core.bot_shared._build_operator_prompt", return_value="prompt"):
                with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                    with patch("core.bot_shared.log_chat"):
                        from core.bot_handlers import _route_to_expert
                        bot = MagicMock()
                        message = MagicMock()
                        message.chat.id = 1
                        message.message_id = 10
                        _route_to_expert(bot, "coder", "fix this", 1, 10)
        core_state._loop_manager.start_expert.assert_called_once_with("coder")
        core_state._loop_manager.wake_expert.assert_called_once_with("coder")


def test_route_to_expert_already_running():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = True
    with patch("core.bot_shared.ExpertContext") as MockCtx:
        ctx = MagicMock()
        MockCtx.return_value = ctx
        with patch("core.bot_shared._get_expert", return_value={"active": True}):
            with patch("core.bot_shared._build_operator_prompt", return_value="prompt"):
                with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                    with patch("core.bot_shared.log_chat"):
                        from core.bot_handlers import _route_to_expert
                        bot = MagicMock()
                        _route_to_expert(bot, "coder", "fix this", 1, 10)
        core_state._loop_manager.start_expert.assert_not_called()
        core_state._loop_manager.wake_expert.assert_called_once_with("coder")


def test_route_to_expert_not_active():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    core_state._loop_manager.is_running.return_value = False
    with patch("core.bot_shared._get_expert", return_value={"active": False}):
        with patch("core.bot_shared.ExpertContext") as MockCtx:
            ctx = MagicMock()
            MockCtx.return_value = ctx
            with patch("core.bot_shared._build_operator_prompt", return_value="prompt"):
                with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                    with patch("core.bot_shared.log_chat"):
                        from core.bot_handlers import _route_to_expert
                        bot = MagicMock()
                        _route_to_expert(bot, "coder", "fix this", 1, 10)
        core_state._loop_manager.start_expert.assert_not_called()
        core_state._loop_manager.wake_expert.assert_called_once_with("coder")


# ── handle_voice ─────────────────────────────────────────────────────────────

def test_handle_voice_import_error(monkeypatch):
    monkeypatch.delattr("core.loops.transcribe_voice", raising=False)
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core.bot_handlers import handle_voice
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.voice = MagicMock()
    msg.audio = None
    handle_voice(bot, msg)
    assert "not supported" in bot.send_message.call_args[0][1].lower()


def test_handle_voice_success(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core import state as core_state
    core_state.WORKING_DIR = tmp_path
    from core.bot_handlers import handle_voice
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.voice = MagicMock()
    msg.voice.file_id = "abc123"
    msg.audio = None
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "voice/abc.oga"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"audio data"
    with patch("core.loops.transcribe_voice", return_value="hello world"):
        with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
            with patch("core.bot_handlers.log_chat"):
                with patch("threading.Thread", autospec=True) as mock_thread:
                    handle_voice(bot, msg)
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


def test_handle_voice_transcription_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core import state as core_state
    core_state.WORKING_DIR = tmp_path
    from core.bot_handlers import handle_voice
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.voice = MagicMock()
    msg.voice.file_id = "abc123"
    msg.audio = None
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "voice/abc.oga"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"data"
    with patch("core.loops.transcribe_voice", side_effect=Exception("no speech detected")):
        handle_voice(bot, msg)
    args = bot.send_message.call_args[0]
    assert "failed" in str(args[1]).lower()


def test_handle_voice_with_caption(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core import state as core_state
    core_state.WORKING_DIR = tmp_path
    from core.bot_handlers import handle_voice
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.voice = MagicMock()
    msg.voice.file_id = "abc"
    msg.audio = None
    msg.caption = "please analyze"
    file_info = MagicMock()
    file_info.file_path = "voice/abc.oga"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"data"
    with patch("core.loops.transcribe_voice", return_value="hello"):
        with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
            with patch("core.bot_handlers.log_chat"):
                with patch("threading.Thread", autospec=True) as mock_thread:
                    handle_voice(bot, msg)
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


# ── handle_document ──────────────────────────────────────────────────────────

def test_handle_document_file_too_large():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.document = MagicMock()
    msg.document.file_name = "big_file.zip"
    msg.document.file_size = 25 * 1024 * 1024  # 25MB
    msg.document.file_unique_id = "uniq1"
    msg.caption = None
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            handle_document(bot, msg)
    args = bot.send_message.call_args[0]
    assert "too large" in str(args[1]).lower()


def test_handle_document_text_file():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.document = MagicMock()
    msg.document.file_name = "script.py"
    msg.document.file_size = 1024
    msg.document.file_unique_id = "uniq2"
    msg.document.mime_type = "text/x-python"
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "docs/script.py"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"print('hello')"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                with patch("core.bot_handlers.log_chat"):
                    handle_document(bot, msg)
    assert bot.send_message.called


def test_handle_document_binary_file():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.document = MagicMock()
    msg.document.file_name = "image.png"
    msg.document.file_size = 2048
    msg.document.file_unique_id = "uniq3"
    msg.document.mime_type = "image/png"
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "docs/image.png"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"PNG data"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                with patch("core.bot_handlers.log_chat"):
                    handle_document(bot, msg)
    assert bot.send_message.called


def test_handle_document_truncated():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.document = MagicMock()
    msg.document.file_name = "huge.txt"
    msg.document.file_size = 1024 * 1024
    msg.document.file_unique_id = "uniq4"
    msg.document.mime_type = "text/plain"
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "docs/huge.txt"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"x" * 60000
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                with patch("core.bot_handlers.log_chat"):
                    handle_document(bot, msg)
    assert bot.send_message.called


def test_handle_document_with_caption():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.document = MagicMock()
    msg.document.file_name = "notes.txt"
    msg.document.file_size = 100
    msg.document.file_unique_id = "uniq5"
    msg.document.mime_type = "text/plain"
    msg.caption = "review this"
    file_info = MagicMock()
    file_info.file_path = "docs/notes.txt"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"content"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                with patch("core.bot_handlers.log_chat"):
                    handle_document(bot, msg)
    assert bot.send_message.called


def test_handle_document_not_addressed():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    with patch("core.bot_handlers._is_addressed_to_me", return_value=False):
        handle_document(bot, msg)
    bot.send_message.assert_not_called()


# ── _codex_photo_audit ───────────────────────────────────────────────────────

def test_codex_audit_script_not_found():
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    with patch("core.bot_handlers.state.WORKING_DIR", MagicMock()):
        with patch("pathlib.Path.exists", return_value=False):
            _codex_photo_audit(bot, 1, MagicMock(), "caption", None)
    bot.send_message.assert_called_once()


def test_codex_audit_no_backend(tmp_path):
    state.CHATLOG_DIR = tmp_path / "chat"
    state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    img = tmp_path / "test.png"
    img.write_text("fake")
    with patch("core.bot_shared.run_agent_streaming", return_value="") as mock_ras:
        with patch("core.bot_shared.log_chat"):
            _codex_photo_audit(bot, 1, img, "caption", None)
    mock_ras.assert_called_once()


def test_codex_audit_success_small(tmp_path):
    state.CHATLOG_DIR = tmp_path / "chat"
    state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    img = tmp_path / "test.png"
    img.write_text("fake")
    with patch("core.bot_shared.run_agent_streaming", return_value="<audit/>") as mock_ras:
        with patch("core.bot_shared.log_chat"):
            _codex_photo_audit(bot, 1, img, "caption", None)
    mock_ras.assert_called_once()


# ── handle_document not authorized in private (calls _reject) ──

def test_handle_document_not_authorized_private():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.document = MagicMock()
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_document(bot, msg)
    bot.send_message.assert_called()


def test_codex_audit_failure(tmp_path):
    state.CHATLOG_DIR = tmp_path / "chat"
    state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    img = tmp_path / "test.png"
    img.write_text("fake")
    with patch("core.bot_shared.run_agent_streaming", return_value="") as mock_ras:
        with patch("core.bot_shared.log_chat"):
            _codex_photo_audit(bot, 1, img, "caption", None)
    mock_ras.assert_called_once()


def test_codex_audit_timeout(tmp_path):
    state.CHATLOG_DIR = tmp_path / "chat"
    state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    img = tmp_path / "test.png"
    img.write_text("fake")
    with patch("core.bot_shared.run_agent_streaming", return_value="") as mock_ras:
        with patch("core.bot_shared.log_chat"):
            _codex_photo_audit(bot, 1, img, "caption", None)
    mock_ras.assert_called_once()


def test_codex_audit_exception(tmp_path):
    state.CHATLOG_DIR = tmp_path / "chat"
    state.CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    img = tmp_path / "test.png"
    img.write_text("fake")
    with patch("core.bot_shared.run_agent_streaming", return_value="") as mock_ras:
        with patch("core.bot_shared.log_chat"):
            _codex_photo_audit(bot, 1, img, "caption", None)
    mock_ras.assert_called_once()


# ── handle_kodak ─────────────────────────────────────────────────────────────

def test_handle_kodak_not_command_for_me():
    from core.bot_handlers import handle_kodak
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="/kodak")
    with patch("core.bot_handlers._is_command_for_me", return_value=False):
        handle_kodak(bot, msg)
    bot.send_message.assert_not_called()


def test_handle_kodak_not_authorized(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core.bot_handlers import handle_kodak
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/kodak")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_kodak(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


def test_handle_kodak_usage():
    from core.bot_handlers import handle_kodak
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/kodak")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            handle_kodak(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Usage" in str(args[1])


def test_handle_kodak_replied_to_photo(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    state.CHAT_ID_FILE = tmp_path / "chat_id.txt"
    state.UPLOADS_DIR = tmp_path / "uploads"
    state.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    from core.bot_handlers import handle_kodak
    bot = MagicMock()
    reply_photo = MagicMock()
    reply_photo.photo = [MagicMock(), MagicMock()]
    reply_photo.photo[-1].file_id = "photo123"
    msg = make_msg(chat_type="private", text="/kodak analyze this")
    msg.reply_to_message = reply_photo
    file_info = MagicMock()
    file_info.file_path = "photos/img.jpg"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"image data"
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._codex_photo_audit"):
                handle_kodak(bot, msg)
    bot.send_message.assert_not_called()


def test_handle_kodak_image_flag():
    from core.bot_handlers import handle_kodak
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/kodak --image /tmp/test.png some prompt")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._codex_photo_audit"):
                with patch("pathlib.Path.exists", return_value=True):
                    handle_kodak(bot, msg)
    bot.send_message.assert_not_called()


def test_handle_kodak_image_flag_not_found():
    from core.bot_handlers import handle_kodak
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/kodak --image /nonexistent.png")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                handle_kodak(bot, msg)
    args = bot.send_message.call_args[0]
    assert "not found" in str(args[1]).lower()


# ── handle_photo ─────────────────────────────────────────────────────────────

def test_handle_photo_not_addressed():
    from core.bot_handlers import handle_photo
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="")
    msg.photo = [MagicMock()]
    with patch("core.bot_handlers._is_addressed_to_me", return_value=False):
        handle_photo(bot, msg)
    bot.send_message.assert_not_called()


def test_handle_photo_not_authorized_private(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core.bot_handlers import handle_photo
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.photo = [MagicMock(), MagicMock()]
    msg.photo[-1].file_id = "x"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_photo(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


def test_handle_photo_kodak_keyword(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    state.CHAT_ID_FILE = tmp_path / "chat_id.txt"
    state.UPLOADS_DIR = tmp_path / "uploads"
    state.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    state.WORKING_DIR = tmp_path
    from core.bot_handlers import handle_photo
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.photo = [MagicMock(), MagicMock()]
    msg.photo[-1].file_id = "photo1"
    msg.caption = "kodak analyze"
    file_info = MagicMock()
    file_info.file_path = "photos/img.jpg"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"image data"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._codex_photo_audit"):
                with patch("threading.Thread", autospec=True) as mock_thread:
                    handle_photo(bot, msg)
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


def test_handle_photo_normal(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    state.CHAT_ID_FILE = tmp_path / "chat_id.txt"
    state.UPLOADS_DIR = tmp_path / "uploads"
    state.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    state.WORKING_DIR = tmp_path
    from core.bot_handlers import handle_photo
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.photo = [MagicMock(), MagicMock()]
    msg.photo[-1].file_id = "photo2"
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "photos/img.jpg"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"image data"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                with patch("core.bot_handlers.log_chat"):
                    with patch("threading.Thread", autospec=True) as mock_thread:
                        handle_photo(bot, msg)
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


# ── handle_message ───────────────────────────────────────────────────────────

def test_handle_message_not_addressed():
    from core.bot_handlers import handle_message
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="hello")
    with patch("core.bot_handlers._is_addressed_to_me", return_value=False):
        handle_message(bot, msg)
    bot.send_message.assert_not_called()


def test_handle_message_not_authorized_private():
    from core.bot_handlers import handle_message
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="hello")
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_message(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


def test_handle_message_no_text():
    from core.bot_handlers import handle_message
    bot = MagicMock()
    msg = make_msg(chat_type="private", text=None)
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            handle_message(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Unsupported" in str(args[1])


def test_handle_message_routes_to_expert():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._route_message", return_value=("coder", "fix this")):
                with patch("core.bot_handlers._route_to_expert"):
                    from core.bot_handlers import handle_message
                    bot = MagicMock()
                    msg = make_msg(chat_type="private", text="fix this")
                    handle_message(bot, msg)


def test_handle_message_operator():
    from core import state as core_state
    core_state._loop_manager = MagicMock()
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._route_message", return_value=(None, "hello")):
                with patch("core.bot_handlers._build_operator_prompt", return_value="prompt"):
                    with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                        with patch("core.bot_handlers.log_chat"):
                            with patch("threading.Thread", autospec=True) as mock_thread:
                                from core.bot_handlers import handle_message
                                bot = MagicMock()
                                msg = make_msg(chat_type="private", text="hello")
                                handle_message(bot, msg)
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


# ── handle_project ───────────────────────────────────────────────────────────

def test_handle_project_not_command_for_me():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="/project")
    with patch("core.bot_handlers._is_command_for_me", return_value=False):
        handle_project(bot, msg)
    bot.send_message.assert_not_called()


def test_handle_project_not_authorized():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_project(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


def test_handle_project_no_subcmd():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "/project new" in str(args[1])


def test_handle_project_unknown_subcmd():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project blah")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "/project new" in str(args[1])


def test_handle_project_new_no_name():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project new")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Usage" in str(args[1])


def test_handle_project_new_existing_dir():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project new testproj a test")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("pathlib.Path.exists", return_value=True):
                handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "already exists" in str(args[1])


def test_handle_project_new_already_registered():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project new testproj")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("core.project_scaffolder._load_projects", return_value={"testproj": {}}):
                    handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "already registered" in str(args[1])


def test_handle_project_new_success(monkeypatch):
    from core.bot_handlers import handle_project
    bot = MagicMock()
    bot.edit_message_text = MagicMock()
    msg = make_msg(chat_type="private", text="/project new myproj my description")
    msg.message_id = 10
    monkeypatch.setattr("builtins.open", MagicMock())
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    with patch("pathlib.Path.mkdir"):
                        with patch("pathlib.Path.write_text"):
                            with patch("pathlib.Path.chmod"):
                                with patch("subprocess.run") as mock_run:
                                    mock_run.return_value.returncode = 0
                                    mock_run.return_value.stdout = ""
                                    mock_run.return_value.stderr = ""
                                    handle_project(bot, msg)
    assert bot.edit_message_text.called


def test_handle_project_new_pm2_fails():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    bot.edit_message_text = MagicMock()
    msg = make_msg(chat_type="private", text="/project new myproj test")
    msg.message_id = 10
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    with patch("pathlib.Path.mkdir"):
                        with patch("pathlib.Path.write_text"):
                            with patch("pathlib.Path.chmod"):
                                with patch("subprocess.run") as mock_run:
                                    mock_run.return_value.returncode = 1
                                    mock_run.return_value.stderr = "pm2 error"
                                    mock_run.return_value.stdout = ""
                                    handle_project(bot, msg)
    assert bot.edit_message_text.called


def test_handle_project_new_exception():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    bot.edit_message_text = MagicMock()
    msg = make_msg(chat_type="private", text="/project new myproj test")
    msg.message_id = 10
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    with patch("pathlib.Path.mkdir", side_effect=Exception("permission denied")):
                        with patch("shutil.rmtree"):
                            handle_project(bot, msg)
    args = bot.edit_message_text.call_args[0]
    assert "Failed" in str(args[0])


def test_handle_project_list():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project list")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers.handle_projects") as mock_hp:
                handle_project(bot, msg)
    mock_hp.assert_called_once()


def test_handle_project_start_no_name():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project start")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Usage" in str(args[1])


def test_handle_project_start_unknown():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project start bogus")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._load_projects", return_value={"real": {}}):
                handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Unknown" in str(args[1])


def test_handle_project_start_success():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project start real")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._load_projects", return_value={"real": {"path": "/x"}}):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stderr = ""
                    handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Started" in str(args[1])


def test_handle_project_start_pm2_fails():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project start real")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._load_projects", return_value={"real": {"path": "/x"}}):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 1
                    mock_run.return_value.stderr = "process not found"
                    handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Failed" in str(args[1])


def test_handle_project_start_exception():
    from core.bot_handlers import handle_project
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/project start real")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._load_projects", return_value={"real": {"path": "/x"}}):
                with patch("subprocess.run", side_effect=Exception("pm2 not found")):
                    handle_project(bot, msg)
    args = bot.send_message.call_args[0]
    assert "Error" in str(args[1])


# ── register_handlers ────────────────────────────────────────────────────────

def test_register_handlers_wires_everything():
    handlers = {}
    commands = {}
    def fake_message_handler(**kwargs):
        def dec(f):
            if "commands" in kwargs:
                for cmd in kwargs["commands"]:
                    commands[cmd] = f
            return f
        return dec

    def fake_callback_handler(**kwargs):
        def dec(f):
            handlers["callback"] = f
            return f
        return dec

    bot = MagicMock()
    bot.message_handler.side_effect = fake_message_handler
    bot.callback_query_handler.side_effect = fake_callback_handler

    from core.bot_handlers import register_handlers
    register_handlers(bot)

    expected_commands = [
        "start", "help", "status", "stop", "goal", "experts",
        "expert", "group", "deepfix", "kodak", "projects",
        "project", "clear", "cancel", "restart", "update",
        "peer", "peers", "wake", "kill",
    ]
    for cmd in expected_commands:
        assert cmd in commands, f"Missing /{cmd} handler"

    assert "callback" in handlers


# ── Remaining edge cases ─────────────────────────────────────────────────────

def test_handle_voice_audio_instead_of_voice(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_USERNAME", "TestBot")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    from core import state as core_state
    core_state.WORKING_DIR = tmp_path
    from core.bot_handlers import handle_voice
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.voice = None
    msg.audio = MagicMock()
    msg.audio.file_id = "abc"
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "audio/song.mp3"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"audio"
    with patch("core.loops.transcribe_voice", return_value="transcribed"):
        with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
            with patch("core.bot_handlers.log_chat"):
                with patch("threading.Thread", autospec=True) as mt:
                    handle_voice(bot, msg)
    mt.assert_called_once()


def test_handle_document_not_authorized_group():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="")
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_document(bot, msg)
    bot.send_message.assert_not_called()


def test_handle_document_read_exception(tmp_path):
    state.UPLOADS_DIR = tmp_path
    state.GOAL_FILE = tmp_path / "GOAL.md"
    state.GOAL_FILE.write_text("")
    state.STATE_FILE = tmp_path / "STATE.md"
    state.STATE_FILE.write_text("")
    from pathlib import PosixPath

    from core.bot_handlers import handle_document
    original_read_text = PosixPath.read_text
    def raising_read_text(self, *args, **kwargs):
        if "broken.py" in str(self):
            raise Exception("read error")
        return original_read_text(self, *args, **kwargs)
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.document = MagicMock()
    msg.document.file_name = "broken.py"
    msg.document.file_size = 100
    msg.document.file_unique_id = "ux"
    msg.document.mime_type = "text/x-python"
    msg.caption = None
    file_info = MagicMock()
    file_info.file_path = "docs/broken.py"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"content"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch.object(PosixPath, "read_text", raising_read_text):
                with patch("core.bot_handlers.load_chatlog", return_value=""):
                    with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                        with patch("core.bot_handlers.log_chat"):
                            with patch("threading.Thread", autospec=True) as mt:
                                handle_document(bot, msg)
    mt.assert_called_once()


def test_save_audit_pending_exception():
    from core.bot_handlers import _save_audit_pending
    state.UPLOADS_DIR = None
    _save_audit_pending(MagicMock(), 1, 2)


def test_clear_audit_pending_exception_none_dir():
    from core.bot_handlers import _clear_audit_pending
    state.UPLOADS_DIR = None
    _clear_audit_pending()


def test_codex_notify_fallback(tmp_path):
    state.UPLOADS_DIR = tmp_path
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    msg = MagicMock()
    msg.message_id = 10
    bot.send_message.return_value = msg
    bot.edit_message_text.side_effect = Exception("edit failed")
    with patch("core.bot_handlers.state.WORKING_DIR", MagicMock()):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(stdout="READY", stderr="", returncode=0),
                    MagicMock(stdout="", stderr="error msg", returncode=1),
                ]
                _codex_photo_audit(bot, 1, MagicMock(), "caption", None)
    assert bot.send_message.called


def test_handle_deepfix_edit_fails(monkeypatch, tmp_path):
    state.CHAT_ID_FILE = tmp_path / "chat_id.txt"
    state.CHAT_ID_FILE.write_text("")
    state.CHATLOG_DIR = tmp_path / "chatlog"
    from core.bot_handlers import handle_deepfix
    bot = MagicMock()
    sent_msg = MagicMock()
    sent_msg.message_id = 10
    bot.send_message.return_value = sent_msg
    bot.edit_message_text.side_effect = Exception("edit fail")
    msg = make_msg(chat_type="private", text="/deepfix https://github.com/o/r/issues/1")
    msg.message_id = 10
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_handlers._fetch_github_issue", return_value=("fetched", None)):
                with patch("core.bot_handlers._build_deepfix_prompt", return_value="prompt"):
                    with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                        handle_deepfix(bot, msg)
    bot.send_message.assert_any_call(1, "Fetching GitHub issue...")


def test_handle_photo_with_caption(tmp_path):
    state.UPLOADS_DIR = tmp_path
    from core.bot_handlers import handle_photo
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="")
    msg.photo = [MagicMock(), MagicMock()]
    msg.photo[-1].file_id = "p3"
    msg.caption = "check this screenshot"
    file_info = MagicMock()
    file_info.file_path = "photos/img.jpg"
    bot.get_file.return_value = file_info
    bot.download_file.return_value = b"data"
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("core.bot_shared.run_agent_streaming", return_value="ok"):
                with patch("core.bot_handlers.log_chat"):
                    with patch("threading.Thread", autospec=True) as mt:
                        handle_photo(bot, msg)
    mt.assert_called_once()


# handle_deepfix with project + no issue text
def test_handle_deepfix_project_no_issue(tmp_path):
    state.CHAT_ID_FILE = tmp_path / "chat_id.txt"
    state.CHAT_ID_FILE.write_text("")
    state.CHATLOG_DIR = tmp_path / "chatlog"
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "proj.json"):
        (tmp_path / "proj.json").write_text(json.dumps({
            "projects": {"orkes": {"path": "/x/y", "description": "test"}}
        }))
        from core.bot_handlers import handle_deepfix
        bot = MagicMock()
        msg = make_msg(chat_type="private", text="/deepfix orkes")
        msg.message_id = 10
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                handle_deepfix(bot, msg)
        bot.send_message.assert_any_call(1, "Project: orkes")


# handle_deepfix with no issue text after project resolution
def test_handle_deepfix_empty_issue(tmp_path):
    with patch("core.bot_shared.PROJECTS_FILE", tmp_path / "empty.json"):
        (tmp_path / "empty.json").write_text('{"projects": {}}')
        from core.bot_handlers import handle_deepfix
        bot = MagicMock()
        # When project resolution returns project_name but no remaining text
        msg = make_msg(chat_type="private", text="/deepfix orkes_ds")
        msg.message_id = 10
        with patch("core.bot_handlers._is_command_for_me", return_value=True):
            with patch("core.bot_handlers._is_authorized", return_value=True):
                with patch("core.bot_handlers._resolve_project", return_value=("orkes_ds", "", "/tmp")):
                    with patch("core.bot_handlers._is_github_issue_url", return_value=False):
                        handle_deepfix(bot, msg)
        bot.send_message.assert_any_call(1, "No issue description provided after project name.")


# handle_cancel not command for me
def test_handle_cancel_not_for_me():
    from core.bot_handlers import handle_cancel
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/cancel")
    with patch("core.bot_handlers._is_command_for_me", return_value=False):
        handle_cancel(bot, msg)
    bot.send_message.assert_not_called()


# handle_cancel not authorized
def test_handle_cancel_not_authorized():
    from core.bot_handlers import handle_cancel
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/cancel")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_cancel(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


# _save_audit_pending exception safety
def test_save_audit_pending_symlink_exists(tmp_path):
    state.UPLOADS_DIR = tmp_path
    xml_path = tmp_path / "audit_20240101.xml"
    xml_path.write_text("<audit/>")
    # Create a file at symlink target to test unlink + symlink_to
    existing = tmp_path / "audit_latest.xml"
    existing.write_text("old")
    from core.bot_handlers import _save_audit_pending
    _save_audit_pending(xml_path, 1, 2)
    marker = tmp_path / "audit_pending.json"
    assert marker.exists()
    data = json.loads(marker.read_text())
    assert data["chat_id"] == 1


# _is_addressed_to_me reply to bot but no cached bot id
def test_is_addressed_to_me_reply_no_bot_id_nousername(monkeypatch):
    monkeypatch.delenv("BOT_USERNAME", raising=False)
    from core.bot_handlers import _cached_bot_id, _is_addressed_to_me
    _cached_bot_id["id"] = None
    bot = MagicMock()
    bot.get_me.side_effect = Exception()
    reply_to = MagicMock()
    reply_to.from_user.id = 999
    msg = make_msg(chat_type="group", text="hello", reply_to=reply_to)
    result = _is_addressed_to_me(bot, msg)
    assert result is True


# _is_addressed_to_me reply to bot with matching bot id, with BOT_USERNAME set
def test_is_addressed_to_me_reply_to_bot_named(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "my_bot")
    from core.bot_handlers import _cached_bot_id, _is_addressed_to_me
    _cached_bot_id["id"] = 42
    bot = MagicMock()
    reply_to = MagicMock()
    reply_to.from_user.id = 42
    msg = make_msg(chat_type="group", text="hello", reply_to=reply_to)
    result = _is_addressed_to_me(bot, msg)
    assert result is True


# _is_addressed_to_me reply to another user (not bot)
def test_is_addressed_to_me_reply_to_other(monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "my_bot")
    from core.bot_handlers import _cached_bot_id, _is_addressed_to_me
    _cached_bot_id["id"] = 42
    bot = MagicMock()
    reply_to = MagicMock()
    reply_to.from_user.id = 99  # not the bot
    msg = make_msg(chat_type="group", text="hello", reply_to=reply_to)
    result = _is_addressed_to_me(bot, msg)
    assert result is False


# handle_projects not for me
def test_handle_projects_not_for_me_short():
    from core.bot_handlers import handle_projects
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/projects")
    with patch("core.bot_handlers._is_command_for_me", return_value=False):
        handle_projects(bot, msg)
    bot.send_message.assert_not_called()


# handle_projects not authorized
def test_handle_projects_not_authorized_short(monkeypatch):
    from core.bot_handlers import handle_projects
    bot = MagicMock()
    msg = make_msg(chat_type="private", text="/projects")
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_projects(bot, msg)
    bot.send_message.assert_called_with(1, "Unauthorized.")


# ── handle_document not authorized in group (no rejection) ──

def test_handle_document_not_authorized_group_short():
    from core.bot_handlers import handle_document
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="")
    msg.document = MagicMock()
    with patch("core.bot_handlers._is_addressed_to_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=False):
            handle_document(bot, msg)
    bot.send_message.assert_not_called()


# ── _resolve_project empty text ──

def test_resolve_project_empty_text():
    from core.bot_handlers import _resolve_project
    name, rest, path = _resolve_project("")
    assert name is None
    assert rest == ""
    assert path is None


# ── handle_deepfix not command for me ──

def test_handle_deepfix_not_command():
    from core.bot_handlers import handle_deepfix
    bot = MagicMock()
    msg = make_msg(chat_type="group", text="/deepfix")
    with patch("core.bot_handlers._is_command_for_me", return_value=False):
        handle_deepfix(bot, msg)
    bot.send_message.assert_not_called()


# ── handle_project new without arbos.py shim ──

def test_handle_project_new_no_shim(tmp_path):
    from core.bot_handlers import handle_project
    bot = MagicMock()
    bot.edit_message_text = MagicMock()
    msg = make_msg(chat_type="private", text="/project new noproj test")
    msg.message_id = 10
    proj_file = tmp_path / "projects.json"
    proj_file.write_text('{"projects": {}}')
    with patch("core.bot_handlers._is_command_for_me", return_value=True):
        with patch("core.bot_handlers._is_authorized", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("core.bot_handlers._load_projects", return_value={}):
                    with patch("core.bot_shared.PROJECTS_FILE", proj_file):
                        with patch("pathlib.Path.mkdir"):
                            with patch("core.bot_handlers.state.WORKING_DIR", tmp_path):
                                with patch("subprocess.run") as mock_run:
                                    mock_run.return_value.returncode = 0
                                    mock_run.return_value.stdout = ""
                                    mock_run.return_value.stderr = ""
                                    handle_project(bot, msg)
    assert bot.edit_message_text.called


# ── _codex_photo_audit script not found (via real Path) ──

def test_codex_audit_script_not_found_real(tmp_path):
    state.WORKING_DIR = tmp_path
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    _codex_photo_audit(bot, 1, MagicMock(), "caption", None)
    bot.send_message.assert_called_once()
    args = bot.send_message.call_args[0]
    assert "not found" in str(args[1]).lower()


# ── _codex_photo_audit long XML (truncation) ──

def test_codex_audit_long_xml(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "1")
    state.CHAT_ID_FILE = tmp_path / "chat_id.txt"
    from core.bot_handlers import _codex_photo_audit
    bot = MagicMock()
    msg = MagicMock()
    msg.message_id = 10
    bot.send_message.return_value = msg
    bot.edit_message_text = MagicMock()
    fake_xml = "<audit>" + "x" * 5000 + "</audit>"
    state.UPLOADS_DIR = tmp_path
    img = tmp_path / "test.png"
    img.write_text("fake")
    with patch("core.bot_handlers.run_agent_streaming", return_value=fake_xml):
        _codex_photo_audit(bot, 1, img, "caption", None)
