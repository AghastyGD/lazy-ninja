import asyncio
import json

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

from lazy_ninja.errors import LazyNinjaError
from lazy_ninja.middleware.error_handling import ErrorHandlingMiddleware
from lazy_ninja.middleware.process_put_patch import ProcessPutPatchMiddleware


def test_error_handling_middleware_passes_through_response():
    factory = RequestFactory()
    request = factory.get("/")

    middleware = ErrorHandlingMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(request)
    assert response.status_code == 200
    assert response.content == b"ok"


def test_error_handling_middleware_handles_lazy_error():
    factory = RequestFactory()
    request = factory.get("/")

    def view(_):
        raise LazyNinjaError("boom", status_code=418)

    middleware = ErrorHandlingMiddleware(view)
    response = middleware(request)
    assert response.status_code == 418
    payload = json.loads(response.content.decode())
    assert payload["error"]["message"] == "boom"


def test_error_handling_middleware_wraps_generic_exception():
    factory = RequestFactory()
    request = factory.get("/")

    def view(_):
        raise RuntimeError("unexpected")

    middleware = ErrorHandlingMiddleware(view)
    response = middleware(request)
    assert response.status_code == 500
    payload = json.loads(response.content.decode())
    assert payload["error"]["type"] == "LazyNinjaError"


def test_error_handling_middleware_async_call():
    factory = RequestFactory()
    request = factory.get("/")

    async def view(_):
        raise LazyNinjaError("async", status_code=409)

    middleware = ErrorHandlingMiddleware(view)
    response = asyncio.run(middleware.__acall__(request))
    assert response.status_code == 409


def test_process_put_patch_middleware_sync_put_request():
    factory = RequestFactory()
    body = encode_multipart(BOUNDARY, {"name": "sync"})
    request = factory.put("/", data=body, content_type=MULTIPART_CONTENT)

    middleware = ProcessPutPatchMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(request)

    assert response.status_code == 200
    assert request.method == "PUT"
    assert request.POST["name"] == "sync"


def test_process_put_patch_middleware_async_patch_request():
    factory = RequestFactory()
    body = encode_multipart(BOUNDARY, {"name": "async"})
    request = factory.patch("/", data=body, content_type=MULTIPART_CONTENT)

    async def view(req):
        assert req.method == "PATCH"
        return HttpResponse("async")

    middleware = ProcessPutPatchMiddleware(view)
    response = asyncio.run(middleware(request))

    assert response.status_code == 200
    assert request.POST["name"] == "async"
