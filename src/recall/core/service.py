from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from recall.core.llm import BaseLLMClient
from recall.core.models import Note


class NoteService:
    def __init__(self, session: Session, llm_client: BaseLLMClient):
        self.session = session
        self.llm_client = llm_client

    def create_note(self, original_note: str, title: str = "") -> Note:
        normalized_title = title.strip() or None
        note = Note(title=normalized_title, original_note=original_note.strip(), enrichment_status="pending")
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def list_notes(self) -> list[Note]:
        statement = select(Note).order_by(Note.updated_at.desc(), Note.id.desc())
        return list(self.session.scalars(statement).all())

    def get_status_counts(self) -> dict[str, int]:
        pending = self.session.scalar(select(func.count()).where(Note.enrichment_status == "pending")) or 0
        in_progress = self.session.scalar(select(func.count()).where(Note.enrichment_status == "in_progress")) or 0
        done = self.session.scalar(select(func.count()).where(Note.enrichment_status == "done")) or 0
        return {
            "pending": int(pending),
            "in_progress": int(in_progress),
            "done": int(done),
        }

    def get_note(self, note_id: int) -> Note | None:
        return self.session.get(Note, note_id)

    def update_note(self, note_id: int, original_note: str, title: str = "") -> Note | None:
        note = self.get_note(note_id)
        if note is None:
            return None

        note.title = title.strip() or None
        note.original_note = original_note.strip()
        note.elaborated_note = None
        note.tags = None
        note.enrichment_status = "pending"
        note.last_enrichment_error = None
        note.enriched_at = None
        note.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(note)
        return note

    def delete_note(self, note_id: int) -> bool:
        note = self.get_note(note_id)
        if note is None:
            return False

        self.session.delete(note)
        self.session.commit()
        return True

    def search_notes(self, query: str) -> list[Note]:
        normalized = query.strip().lower()
        if not normalized:
            return self.list_notes()

        terms = [term for term in normalized.split() if term]
        statement = select(Note)
        for term in terms:
            pattern = f"%{term}%"
            statement = statement.where(
                or_(
                    Note.title.ilike(pattern),
                    Note.original_note.ilike(pattern),
                    Note.elaborated_note.ilike(pattern),
                    Note.tags.ilike(pattern),
                )
            )
        statement = statement.order_by(Note.updated_at.desc(), Note.id.desc())
        return list(self.session.scalars(statement).all())

    def search_notes_paginated(self, query: str, page: int = 1, page_size: int = 10) -> tuple[list[Note], int]:
        normalized = query.strip().lower()
        if not normalized:
            return [], 0

        terms = [term for term in normalized.split() if term]
        if not terms:
            return [], 0

        statement = select(Note)
        for term in terms:
            pattern = f"%{term}%"
            statement = statement.where(
                or_(
                    Note.title.ilike(pattern),
                    Note.original_note.ilike(pattern),
                    Note.elaborated_note.ilike(pattern),
                    Note.tags.ilike(pattern),
                )
            )

        count_statement = select(func.count()).select_from(statement.subquery())
        total = self.session.scalar(count_statement) or 0

        paged_statement = (
            statement.order_by(Note.updated_at.desc(), Note.id.desc())
            .offset((max(page, 1) - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(paged_statement).all()), total

    def claim_pending_notes(self, limit: int) -> list[Note]:
        statement = (
            select(Note)
            .where(Note.enrichment_status == "pending")
            .order_by(Note.updated_at.asc(), Note.id.asc())
            .limit(limit)
        )
        notes = list(self.session.scalars(statement).all())
        for note in notes:
            note.enrichment_status = "in_progress"
            note.last_enrichment_error = None
        self.session.commit()
        return notes

    def enrich_note(self, note_id: int) -> Note | None:
        note = self.get_note(note_id)
        if note is None:
            return None

        result = self.llm_client.enrich(note.original_note)
        if not note.title:
            note.title = result.title
        note.elaborated_note = result.elaborated_note
        note.tags = ", ".join(result.tags)
        note.enrichment_status = "done"
        note.last_enrichment_error = None
        note.enriched_at = datetime.now(UTC)
        note.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(note)
        return note

    def record_enrichment_failure(self, note_id: int, error_message: str) -> Note | None:
        note = self.get_note(note_id)
        if note is None:
            return None

        note.elaborated_note = None
        note.tags = None
        note.enriched_at = None
        note.enrichment_status = "pending"
        note.last_enrichment_error = error_message
        note.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(note)
        return note
