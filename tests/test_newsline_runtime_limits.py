"""Newsline split parallelism / CPU thread env knobs."""

from __future__ import annotations

import os

import pytest

from app.newsline.engine import runtime_limits


def test_qa_worker_count_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARNEWSLINE_QA_WORKERS", "1")
    assert runtime_limits.qa_worker_count() == 1
    assert runtime_limits.qa_worker_count(requested=3) == 3


def test_export_worker_count_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARNEWSLINE_EXPORT_WORKERS", raising=False)
    assert runtime_limits.export_worker_count() == 4
    monkeypatch.setenv("ARNEWSLINE_EXPORT_WORKERS", "1")
    assert runtime_limits.export_worker_count() == 1


def test_cpu_thread_count_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARNEWSLINE_CPU_THREADS", raising=False)
    assert runtime_limits.cpu_thread_count() is None
    monkeypatch.setenv("ARNEWSLINE_CPU_THREADS", "2")
    assert runtime_limits.cpu_thread_count() == 2


def test_apply_host_thread_caps_sets_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARNEWSLINE_CPU_THREADS", "2")
    monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    runtime_limits.apply_host_thread_caps()
    assert os.environ["OMP_NUM_THREADS"] == "2"
    assert os.environ["MKL_NUM_THREADS"] == "2"
