"""Testes do sequenciador anti-plágio."""

import pytest

from collections import Counter

from app.core.exceptions import AntiPlagiarismError
from app.services.video.schemas import ClipSpec
from app.services.video.sequencer import sequence_clips_anti_plagiarism


def _clips(source: str, count: int) -> list[ClipSpec]:
    return [
        ClipSpec(
            source_video=source,
            start_seconds=index,
            duration_seconds=3,
            clip_index=index,
        )
        for index in range(count)
    ]


def test_empty_input_returns_empty_sequence() -> None:
    """Uma entrada vazia não precisa de tratamento anti-plágio."""
    assert sequence_clips_anti_plagiarism([]) == []


def test_two_uniform_sources_alternate_perfectly() -> None:
    """Dois grupos uniformes devem produzir ABAB."""
    clips = _clips("a.mp4", 3) + _clips("b.mp4", 3)

    sequence = sequence_clips_anti_plagiarism(clips)

    assert [item.clip_spec.source_video for item in sequence] == [
        "a.mp4",
        "b.mp4",
        "a.mp4",
        "b.mp4",
        "a.mp4",
        "b.mp4",
    ]


def test_three_sources_have_no_adjacent_duplicates() -> None:
    """A intercalação deve funcionar com várias fontes."""
    clips = _clips("a.mp4", 2) + _clips("b.mp4", 2) + _clips("c.mp4", 2)

    sequence = sequence_clips_anti_plagiarism(clips)

    sources = [item.clip_spec.source_video for item in sequence]
    assert len(sequence) == len(clips)
    assert all(left != right for left, right in zip(sources, sources[1:]))


def test_preserves_clips_and_assigns_positions() -> None:
    """Nenhum clipe deve ser perdido ou duplicado."""
    clips = _clips("a.mp4", 2) + _clips("b.mp4", 1) + _clips("c.mp4", 1)

    sequence = sequence_clips_anti_plagiarism(clips)

    def key(clip: ClipSpec) -> tuple:
        return (
            clip.source_video,
            clip.start_seconds,
            clip.duration_seconds,
            clip.clip_index,
        )

    assert Counter(key(item.clip_spec) for item in sequence) == Counter(
        key(clip) for clip in clips
    )
    assert [item.sequence_position for item in sequence] == list(range(4))


def test_single_source_raises_actionable_error() -> None:
    """Uma única fonte não permite cumprir a regra anti-plágio."""
    with pytest.raises(AntiPlagiarismError, match="pelo menos dois"):
        sequence_clips_anti_plagiarism(_clips("only.mp4", 2))


def test_impossible_distribution_raises_error() -> None:
    """Uma distribuição muito desbalanceada não deve gerar saída inválida."""
    clips = _clips("a.mp4", 4) + _clips("b.mp4", 1)

    with pytest.raises(AntiPlagiarismError, match="Não é possível"):
        sequence_clips_anti_plagiarism(clips)
