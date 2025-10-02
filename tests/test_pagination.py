import pytest
from ninja.conf import settings as ninja_settings
from ninja.pagination import LimitOffsetPagination, PageNumberPagination

from lazy_ninja.pagination import (
    get_pagination_strategy,
    LimitOffsetPaginationStrategy,
    PageNumberPaginationStrategy,
)


def test_get_pagination_strategy_defaults_to_limit_offset(monkeypatch):
    monkeypatch.setattr(ninja_settings, "PAGINATION_CLASS", None, raising=False)
    strategy = get_pagination_strategy()
    assert isinstance(strategy, LimitOffsetPaginationStrategy)
    assert strategy.get_paginator() is LimitOffsetPagination


def test_get_pagination_strategy_respects_settings(monkeypatch):
    monkeypatch.setattr(
        ninja_settings,
        "PAGINATION_CLASS",
        "ninja.pagination.PageNumberPagination",
        raising=False,
    )
    strategy = get_pagination_strategy()
    assert isinstance(strategy, PageNumberPaginationStrategy)
    assert strategy.get_paginator() is PageNumberPagination


def test_get_pagination_strategy_explicit_type():
    strategy = get_pagination_strategy(pagination_type="page-number")
    assert isinstance(strategy, PageNumberPaginationStrategy)
    assert strategy.get_pagination_class_name() == "PageNumberPagination"


def test_get_pagination_strategy_invalid_type():
    with pytest.raises(ValueError):
        get_pagination_strategy(pagination_type="unknown")
