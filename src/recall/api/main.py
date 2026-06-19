from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from recall.core.config import settings
from recall.core.db import get_session, init_db
from recall.core.llm import build_llm_client
from recall.core.runtime_llm_config import load_or_create_runtime_llm_config
from recall.core.schemas import EnrichmentResponse, NoteCreate, NoteRead, NoteUpdate, SearchResult
from recall.core.service import NoteService


app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_note_service(session: Session = Depends(get_session)) -> NoteService:
    return NoteService(session=session, llm_client=build_llm_client(settings.llm_provider))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/notes", response_model=list[NoteRead])
def list_notes(service: NoteService = Depends(get_note_service)):
    return service.list_notes()


@app.post("/notes", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, service: NoteService = Depends(get_note_service)):
    return service.create_note(payload.original_note, title=payload.title)


@app.get("/notes/{note_id}", response_model=NoteRead)
def get_note(note_id: int, service: NoteService = Depends(get_note_service)):
    note = service.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.put("/notes/{note_id}", response_model=NoteRead)
def update_note(note_id: int, payload: NoteUpdate, service: NoteService = Depends(get_note_service)):
    note = service.update_note(note_id, payload.original_note, title=payload.title)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, service: NoteService = Depends(get_note_service)):
    if not service.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")


@app.get("/search", response_model=SearchResult)
def search_notes(q: str = "", service: NoteService = Depends(get_note_service)):
    return SearchResult(query=q, results=service.search_notes(q))


@app.post("/bot/process-pending", response_model=EnrichmentResponse)
def process_pending_notes(limit: int = 10, session: Session = Depends(get_session)):
    runtime_config, _config_path = load_or_create_runtime_llm_config()
    service = NoteService(
        session=session,
        llm_client=build_llm_client(
            runtime_config.provider,
            ollama_base_url=runtime_config.ollama.base_url,
            ollama_model=runtime_config.ollama.model,
            ollama_timeout_seconds=runtime_config.ollama.timeout_seconds,
        ),
    )
    processed = 0
    for note in service.claim_pending_notes(limit=limit):
        try:
            if service.enrich_note(note.id) is not None:
                processed += 1
        except Exception as exc:  # pragma: no cover - defensive guard for worker/API entrypoint
            service.record_enrichment_failure(note.id, str(exc))
    return EnrichmentResponse(processed=processed)
