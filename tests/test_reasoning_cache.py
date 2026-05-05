"""Tests for reasoning_cache.py — 100% coverage target."""
import json

from core.reasoning_cache import (
    _message_signature,
    _normalize_tool_call,
    _tool_call_ids,
    _tool_call_signature,
)


class TestNormalizeToolCall:
    def test_normalize_typical(self):
        tc = {"id": "call_1", "type": "function", "function": {"name": "Bash", "arguments": '{"command":"ls"}'}}
        result = _normalize_tool_call(tc)
        assert result["id"] == "call_1"
        assert result["type"] == "function"
        assert result["function"]["name"] == "Bash"

    def test_normalize_no_function(self):
        tc = {"id": "call_2"}
        result = _normalize_tool_call(tc)
        assert result["function"]["name"] == ""
        assert result["function"]["arguments"] == ""

    def test_normalize_function_not_dict(self):
        tc = {"id": "call_3", "function": "not a dict"}
        result = _normalize_tool_call(tc)
        assert result["function"]["name"] == ""

    def test_normalize_arguments_not_str(self):
        tc = {"id": "call_4", "function": {"name": "Bash", "arguments": {"cmd": "ls"}}}
        result = _normalize_tool_call(tc)
        parsed = json.loads(result["function"]["arguments"])
        assert parsed == {"cmd": "ls"}

    def test_normalize_missing_type_defaults(self):
        tc = {"id": "call_5", "function": {"name": "Read"}}
        result = _normalize_tool_call(tc)
        assert result["type"] == "function"


class TestMessageSignature:
    def test_signature_empty_content(self):
        sig = _message_signature({"content": "", "tool_calls": []})
        assert isinstance(sig, str) and len(sig) == 64

    def test_signature_with_content(self):
        sig1 = _message_signature({"content": "hello", "tool_calls": []})
        sig2 = _message_signature({"content": "world", "tool_calls": []})
        assert sig1 != sig2

    def test_signature_with_tool_calls(self):
        tc = [{"id": "c1", "function": {"name": "Bash", "arguments": '{"x":"y"}'}}]
        sig = _message_signature({"content": "do it", "tool_calls": tc})
        assert isinstance(sig, str) and len(sig) == 64

    def test_signature_deterministic(self):
        tc = [{"id": "c1", "function": {"name": "Bash", "arguments": '{"x":"y"}'}}]
        sig1 = _message_signature({"content": "test", "tool_calls": tc})
        sig2 = _message_signature({"content": "test", "tool_calls": tc})
        assert sig1 == sig2

    def test_signature_no_tool_calls(self):
        sig = _message_signature({"content": "hello"})
        assert len(sig) == 64

    def test_signature_non_dict_tool_call(self):
        tc = [{"id": "c1"}, "not-a-dict"]
        sig = _message_signature({"content": "x", "tool_calls": tc})
        assert len(sig) == 64


class TestToolCallIds:
    def test_extracts_ids(self):
        msg = {"tool_calls": [{"id": "c1"}, {"id": "c2"}]}
        assert _tool_call_ids(msg) == ["c1", "c2"]

    def test_empty_when_no_calls(self):
        msg = {"tool_calls": []}
        assert _tool_call_ids(msg) == []

    def test_empty_when_no_key(self):
        assert _tool_call_ids({}) == []

    def test_skips_non_dict_calls(self):
        msg = {"tool_calls": [{"id": "c1"}, "bad"]}
        assert _tool_call_ids(msg) == ["c1"]

    def test_skips_missing_id(self):
        msg = {"tool_calls": [{"name": "Bash"}]}
        assert _tool_call_ids(msg) == []


class TestToolCallSignature:
    def test_signature_without_id(self):
        tc = {"id": "c1", "function": {"name": "Bash", "arguments": '{"cmd":"ls"}'}}
        sig = _tool_call_signature(tc)
        assert isinstance(sig, str) and len(sig) == 64

    def test_signature_deterministic(self):
        tc1 = {"id": "c1", "function": {"name": "Bash", "arguments": '{"cmd":"ls"}'}}
        tc2 = {"id": "c2", "function": {"name": "Bash", "arguments": '{"cmd":"ls"}'}}
        assert _tool_call_signature(tc1) == _tool_call_signature(tc2)

    def test_different_inputs_different_sigs(self):
        tc1 = {"function": {"name": "Read", "arguments": '{"file":"a"}'}}
        tc2 = {"function": {"name": "Read", "arguments": '{"file":"b"}'}}
        assert _tool_call_signature(tc1) != _tool_call_signature(tc2)
