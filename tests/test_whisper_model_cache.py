"""Whisper model cache is cleared after a Newsline split pipeline finishes."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

import app.newsline.engine.whisper_model as whisper_model
from app.newsline.engine.models import Boundary, Segment, SegmentKind, WordTiming
from app.newsline.engine.pipeline import run_forced_align_pipeline


def _sample_segment() -> Segment:
    return Segment(
        index=0,
        title="Intro",
        body_lines=("Hello",),
        kind=SegmentKind.INTRO,
        speakable_text="Hello",
    )


def _seed_cache(monkeypatch: pytest.MonkeyPatch, *keys: tuple[str, int]) -> None:
    cache = {key: object() for key in keys}
    monkeypatch.setattr(whisper_model, "_whisper_model_cache", cache)


def test_clear_whisper_models_empties_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_cache(monkeypatch, ("small.en", 0), ("base.en", 0))
    assert whisper_model.cached_whisper_model_count() == 2
    assert whisper_model.clear_whisper_models() == 2
    assert whisper_model.cached_whisper_model_count() == 0
    assert whisper_model.clear_whisper_models() == 0


def test_pipeline_clears_whisper_cache_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seed_cache(monkeypatch, ("small.en", 0), ("small.en", 1))

    def fake_align(
        *_args: object, **_kwargs: object
    ) -> tuple[list[Boundary], list[WordTiming], list[tuple[float, float]] | None]:
        return ([cast(Boundary, MagicMock(spec=Boundary))], [], None)

    monkeypatch.setattr("app.newsline.engine.pipeline.align_segments_forced", fake_align)

    def no_issues(_boundaries: object) -> list[object]:
        return []

    def identity(items: list[object]) -> list[object]:
        return items

    def ignore(*_args: object, **_kwargs: object) -> None:
        return None

    def never_critical(_issue: object, strict: bool = False) -> bool:
        _ = strict
        return False

    monkeypatch.setattr("app.newsline.engine.pipeline._qa_forced_boundaries", no_issues)
    monkeypatch.setattr("app.newsline.engine.pipeline._dedupe_issues", identity)
    monkeypatch.setattr("app.newsline.engine.pipeline._print_issues", ignore)
    monkeypatch.setattr("app.newsline.engine.pipeline.is_critical", never_critical)
    monkeypatch.setattr("app.newsline.engine.pipeline.export_boundaries_json", ignore)
    monkeypatch.setattr("app.newsline.engine.pipeline.write_alignment_report", ignore)

    out = tmp_path / "out"
    out.mkdir()
    _boundaries, _words, critical, _passes, _max_passes = run_forced_align_pipeline(
        audio=tmp_path / "report.mp3",
        report_id=1,
        all_segments=(_sample_segment(),),
        duration=10.0,
        output_dir=out,
        align_model="base.en",
        cache_dir=None,
        dry_run=True,
        reencode=False,
        strict=False,
    )
    assert critical == []
    assert whisper_model.cached_whisper_model_count() == 0


def test_pipeline_clears_whisper_cache_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seed_cache(monkeypatch, ("base.en", 0))

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("align failed")

    monkeypatch.setattr("app.newsline.engine.pipeline.align_segments_forced", boom)

    out = tmp_path / "out"
    out.mkdir()
    try:
        _ = run_forced_align_pipeline(
            audio=tmp_path / "report.mp3",
            report_id=1,
            all_segments=(_sample_segment(),),
            duration=10.0,
            output_dir=out,
            align_model="base.en",
            cache_dir=None,
            dry_run=True,
            reencode=False,
            strict=False,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected align failure")
    assert whisper_model.cached_whisper_model_count() == 0
