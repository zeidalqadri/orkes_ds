"""Module integrity tests — catch missing handler definitions at import time."""

import types

from core import bot_handlers


def _collect_handler_refs() -> set[str]:
    """Parse register_handlers and ALL nested closures to collect handle_* names.

    register_handlers defines inner lambdas like:
        @bot.message_handler(commands=["help"])
        def _help(m): handle_help(bot, m)

    The handle_* references live inside those nested closures, not directly
    in register_handlers, so we must recursively walk all nested code objects.
    """
    seen = set()

    def walk(code):
        if code in seen:
            return
        seen.add(code)
        for name in code.co_names:
            if name.startswith("handle_"):
                yield name
        # Recurse into nested functions/closures
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                yield from walk(const)

    names = set(walk(bot_handlers.register_handlers.__code__))
    return names


def test_all_registered_handlers_are_defined():
    """Every handle_* function referenced in register_handlers must exist in the module."""
    refs = _collect_handler_refs()
    assert refs, "No handle_* references found — introspection may be broken"

    missing = []
    for name in sorted(refs):
        obj = getattr(bot_handlers, name, None)
        if not callable(obj):
            missing.append(name)

    assert not missing, (
        f"{len(missing)} handler(s) referenced in register_handlers() "
        f"but not defined in bot_handlers:\n  " + "\n  ".join(missing)
    )


def test_register_handlers_is_callable():
    """register_handlers itself should be a callable function."""
    assert callable(bot_handlers.register_handlers)


def test_register_handlers_accepts_bot_arg():
    """register_handlers should accept a bot argument."""
    assert "bot" in bot_handlers.register_handlers.__code__.co_varnames[:3]
