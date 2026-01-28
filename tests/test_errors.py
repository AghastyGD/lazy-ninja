import asyncio
import json

import pytest
from django.core import exceptions
from django.db import DatabaseError
from django.http import JsonResponse

from ninja.errors import HttpError

from lazy_ninja.errors import (
    handle_exception,
    handle_exception_async,
    LazyNinjaError,
    ValidationError,
    NotFoundError,
    PermissionDeniedError,
    DatabaseOperationError,
    SynchronousOperationError,
)

from tests.models import TestModel


def _extract_payload(response: JsonResponse) -> dict:
    assert response.status_code
    data = json.loads(response.content.decode())
    assert "error" in data
    return data["error"]


@pytest.mark.parametrize(
    "exception,expected_type,expected_status",
    [
        (TestModel.DoesNotExist("missing"), NotFoundError, 404),
        (exceptions.ObjectDoesNotExist("missing"), NotFoundError, 404),
        (PermissionError("denied"), PermissionDeniedError, 403),
        (exceptions.ValidationError("invalid"), ValidationError, 400),
        (ValueError("bad"), ValidationError, 400),
        (DatabaseError("db error"), DatabaseOperationError, 500),
        (exceptions.SynchronousOnlyOperation("sync"), SynchronousOperationError, 500),
        (HttpError(401, "unauthorized"), LazyNinjaError, 401),
    ],
)
def test_handle_exception_maps_common_errors(exception, expected_type, expected_status, settings):
    settings.DEBUG = False
    response = handle_exception(exception)
    assert response.status_code == expected_status
    error = _extract_payload(response)
    assert error["type"] == expected_type.__name__


def test_handle_exception_preserves_lazy_ninja_error():
    error = LazyNinjaError("boom", status_code=499)
    response = handle_exception(error)
    assert response.status_code == 499
    payload = _extract_payload(response)
    assert payload["message"] == "boom"
    assert payload["type"] == "LazyNinjaError"


def test_handle_exception_defaults_to_generic_error(settings, capsys):
    settings.DEBUG = True
    response = handle_exception(RuntimeError("crash"))
    assert response.status_code == 500
    payload = _extract_payload(response)
    assert payload["type"] == "LazyNinjaError"
    captured = capsys.readouterr().out
    assert "LazyNinja" in captured


def test_handle_exception_async_delegates_to_sync():
    async def run():
        response = await handle_exception_async(TestModel.DoesNotExist("async"))
        return response.status_code

    status = asyncio.run(run())
    assert status == 404
