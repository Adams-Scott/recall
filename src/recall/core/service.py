from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from recall.core.llm import BaseLLMClient
from recall.core.models import Note


class NoteService:
    def __init__(self, session: Session, llm_client: BaseLLMClient):
        self.session = session
        self.llm_client = llm_client

    def create_note(self, original_note: str) -> Note:
        note = Note(original_note=original_note.strip(), enrichment_status="pending")
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def list_notes(self) -> list[Note]:
        statement = select(Note).order_by(Note.updated_at.desc(), Note.id.desc())
        return list(self.session.scalars(statement).all())

    def get_note(self, note_id: int) -> Note | None:
        return self.session.get(Note, note_id)

    def update_note(self, note_id: int, original_note: str) -> Note | None:
        note = self.get_note(note_id)
        if note is None:
            return None

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
                    Note.original_note.ilike(pattern),
                    Note.elaborated_note.ilike(pattern),
                    Note.tags.ilike(pattern),
                )
            )
        statement = statement.order_by(Note.updated_at.desc(), Note.id.desc())
        return list(self.session.scalars(statement).all())

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

        note.enrichment_status = "error"
        note.last_enrichment_error = error_message
        note.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(note)
        return note
