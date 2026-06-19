from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from recall.core.config import settings
from recall.core.db import get_session, init_db
from recall.core.llm import build_llm_client
from recall.core.service import NoteService


app = FastAPI(title=f"{settings.app_name} Web")
base_path = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(base_path / "templates"))
app.mount("/static", StaticFiles(directory=str(base_path / "static")), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_note_service(session: Session = Depends(get_session)) -> NoteService:
    return NoteService(session=session, llm_client=build_llm_client(settings.llm_provider))


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", service: NoteService = Depends(get_note_service)):
    notes = service.search_notes(q) if q else service.list_notes()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "notes": notes,
            "query": q,
        },
    )


@app.post("/notes")
def create_note(original_note: str = Form(...), service: NoteService = Depends(get_note_service)):
    service.create_note(original_note)
    return RedirectResponse(url="/", status_code=303)


@app.get("/notes/{note_id}", response_class=HTMLResponse)
def note_detail(request: Request, note_id: int, service: NoteService = Depends(get_note_service)):
    note = service.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "note": note,
        },
    )


@app.get("/notes/{note_id}/edit", response_class=HTMLResponse)
def edit_note(request: Request, note_id: int, service: NoteService = Depends(get_note_service)):
    note = service.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "note": note,
        },
    )


@app.post("/notes/{note_id}/edit")
def save_note(note_id: int, original_note: str = Form(...), service: NoteService = Depends(get_note_service)):
    if service.update_note(note_id, original_note) is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return RedirectResponse(url=f"/notes/{note_id}", status_code=303)


@app.post("/notes/{note_id}/delete")
def delete_note(note_id: int, service: NoteService = Depends(get_note_service)):
    if not service.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return RedirectResponse(url="/", status_code=303)
