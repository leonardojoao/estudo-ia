"""Sequenciamento anti-plágio de clipes."""

import heapq
from collections import defaultdict, deque

from app.core.exceptions import AntiPlagiarismError

from .schemas import ClipSpec, SequencedClip


def _pop_different_group(
    heap: list[tuple[int, str]],
    groups: dict[str, deque[ClipSpec]],
    last_source: str | None,
) -> tuple[int, str]:
    """Retira o maior grupo cuja fonte difere da última usada."""
    skipped: list[tuple[int, str]] = []
    selected: tuple[int, str] | None = None
    while heap:
        candidate = heapq.heappop(heap)
        if candidate[1] != last_source:
            selected = candidate
            break
        skipped.append(candidate)

    for candidate in skipped:
        heapq.heappush(heap, candidate)
    if selected is None:
        raise AntiPlagiarismError(
            "Não é possível evitar clipes consecutivos da mesma fonte; "
            "adicione mais vídeos ou redistribua os clipes"
        )
    return selected


def sequence_clips_anti_plagiarism(
    clips: list[ClipSpec],
) -> list[SequencedClip]:
    """Intercala clipes de fontes diferentes usando um max-heap."""
    if not clips:
        return []

    groups: dict[str, deque[ClipSpec]] = defaultdict(deque)
    for clip in clips:
        groups[clip.source_video].append(clip)
    if len(groups) == 1:
        raise AntiPlagiarismError(
            "A sequência precisa de pelo menos dois vídeos-fonte; "
            "adicione mais vídeos para aplicar anti-plágio"
        )

    heap = [(-len(group), source) for source, group in groups.items()]
    heapq.heapify(heap)
    sequence: list[SequencedClip] = []
    last_source: str | None = None

    while heap:
        _, source = _pop_different_group(heap, groups, last_source)
        clip = groups[source].popleft()
        sequence.append(
            SequencedClip(
                clip_spec=clip,
                sequence_position=len(sequence),
            )
        )
        last_source = source
        if groups[source]:
            heapq.heappush(heap, (-len(groups[source]), source))

    for previous, current in zip(sequence, sequence[1:]):
        if previous.clip_spec.source_video == current.clip_spec.source_video:
            raise AntiPlagiarismError(
                "A sequência gerada contém fontes consecutivas; "
                "adicione mais vídeos ou redistribua os clipes"
            )
    return sequence
