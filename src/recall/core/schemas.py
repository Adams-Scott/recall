from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    original_note: str = Field(min_length=1)


class NoteUpdate(BaseModel):
    original_note: str = Field(min_length=1)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_note: str
    elaborated_note: str | None
    tags: str | None
    enrichment_status: str
    last_enrichment_error: str | None
    created_at: datetime
    updated_at: datetime
    enriched_at: datetime | None


class SearchResult(BaseModel):
    query: str
    results: list[NoteRead]


class EnrichmentResponse(BaseModel):
    processed: int
