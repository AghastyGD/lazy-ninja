import pytest
from tests.async_support import run_async

from lazy_ninja.utils.hooks import (
    SyncHookExecutor,
    AsyncHookExecutor,
    execute_hook,
    execute_hook_async,
    get_hook,
)


def test_sync_hook_executor_executes_callable():
    executor = SyncHookExecutor()
    result = executor.execute(lambda value: value.upper(), "sync")
    assert result == "SYNC"


def test_async_hook_executor_executes_callable():
    executor = AsyncHookExecutor()
    result = run_async(executor.execute(lambda value: value.lower(), "ASYNC"))
    assert result == "async"


def test_execute_hook_helpers(monkeypatch):
    calls = {}

    def sync_hook(value):
        calls["sync"] = value
        return value

    async_result = run_async(execute_hook_async(sync_hook, "payload"))
    assert async_result == "payload"

    sync_result = execute_hook(sync_hook, "payload")
    assert sync_result == "payload"
    assert calls["sync"] == "payload"


def test_get_hook_prefers_controller_methods():
    class Controller:
        def before_create(self, value):
            return value

    controller = Controller()
    hook = get_hook(controller, "before_create")
    assert hook is not None
    assert hook("data") == "data"


def test_get_hook_falls_back_to_passed_hook():
    def fallback(value):
        return value

    class Controller:
        def before_create(self, value):
            return value

    controller = Controller()
    Controller.before_create.__is_default_hook__ = True
    hook = get_hook(controller, "before_create", passed_hook=fallback)
    assert hook is fallback
