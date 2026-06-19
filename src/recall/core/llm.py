from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
import re


@dataclass(frozen=True)
class EnrichmentResult:
    title: str
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
        title = _generate_title(note_text, keywords)
        elaborated = (
            "Original note: "
            f"{note_text.strip()}\n\n"
            "Elaboration: This note has been expanded into a clearer memory aid. "
            f"Key themes include {', '.join(tags)}."
        )
        return EnrichmentResult(title=title, elaborated_note=elaborated, tags=tags)


def _top_keywords(words: Iterable[str]) -> list[str]:
    counts: dict[str, int] = {}
    stop_words = {"the", "and", "for", "with", "this", "that", "from", "have", "you", "your", "are", "was", "were", "will", "into", "about", "note", "remember"}
    for word in words:
        if len(word) < 3 or word in stop_words:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _generate_title(note_text: str, keywords: list[str]) -> str:
    if keywords:
        title_words = [word.capitalize() for word in keywords[:4]]
        return " ".join(title_words)

    words = re.findall(r"[A-Za-z0-9']+", note_text.strip())
    if words:
        return " ".join(words[:6])[:80]

    return "Untitled Note"


def build_llm_client(provider: str) -> BaseLLMClient:
    return HeuristicLLMClient()
