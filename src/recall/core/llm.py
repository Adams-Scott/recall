from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
import re


@dataclass(frozen=True)
class EnrichmentResult:
    elaborated_note: str
    tags: list[str]


class BaseLLMClient:
    def enrich(self, note_text: str) -> EnrichmentResult:
        raise NotImplementedError


class HeuristicLLMClient(BaseLLMClient):
    def enrich(self, note_text: str) -> EnrichmentResult:
        words = re.findall(r"[A-Za-z0-9']+", note_text.lower())
        keywords = _top_keywords(words)
        tags = keywords[:5] or ["note"]
        elaborated = (
            "Original note: "
            f"{note_text.strip()}\n\n"
            "Elaboration: This note has been expanded into a clearer memory aid. "
            f"Key themes include {', '.join(tags)}."
        )
        return EnrichmentResult(elaborated_note=elaborated, tags=tags)


def _top_keywords(words: Iterable[str]) -> list[str]:
    counts: dict[str, int] = {}
    stop_words = {"the", "and", "for", "with", "this", "that", "from", "have", "you", "your", "are", "was", "were", "will", "into", "about", "note", "remember"}
    for word in words:
        if len(word) < 3 or word in stop_words:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def build_llm_client(provider: str) -> BaseLLMClient:
    return HeuristicLLMClient()
