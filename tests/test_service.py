from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from recall.core.db import Base
from recall.core.llm import HeuristicLLMClient
from recall.core.service import NoteService


def make_service(tmp_path: Path) -> NoteService:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return NoteService(session=session_factory(), llm_client=HeuristicLLMClient())


def test_create_and_search_notes(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.create_note("Remember the code for the garage door")
    service.create_note("Buy coffee beans on Thursday")
    results = service.search_notes("garage")
    assert len(results) == 1
    assert results[0].original_note == "Remember the code for the garage door"


def test_enrich_note_preserves_original_text(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    note = service.create_note("Pack sunscreen for the trip")
    enriched = service.enrich_note(note.id)
    assert enriched is not None
    assert enriched.original_note == "Pack sunscreen for the trip"
    assert enriched.elaborated_note is not None
    assert enriched.tags is not None


def test_update_resets_enrichment_state(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    note = service.create_note("Pick up dry cleaning")
    service.enrich_note(note.id)
    updated = service.update_note(note.id, "Pick up dry cleaning after work")
    assert updated is not None
    assert updated.elaborated_note is None
    assert updated.tags is None
    assert updated.enrichment_status == "pending"


def test_enrich_fills_title_when_empty(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    note = service.create_note("Submit travel reimbursement on Monday", title="")
    assert note.title is None

    enriched = service.enrich_note(note.id)
    assert enriched is not None
    assert enriched.title is not None
    assert enriched.title != ""


def test_search_notes_paginated_uses_page_size_ten(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    for idx in range(25):
        service.create_note(f"Project alpha task {idx}", title=f"Alpha {idx}")

    page_one, total = service.search_notes_paginated("alpha", page=1, page_size=10)
    page_three, _ = service.search_notes_paginated("alpha", page=3, page_size=10)

    assert total == 25
    assert len(page_one) == 10
    assert len(page_three) == 5
