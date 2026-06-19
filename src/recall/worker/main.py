from __future__ import annotations

import time

from apscheduler.schedulers.background import BackgroundScheduler

from recall.core.config import settings
from recall.core.db import SessionLocal, init_db
from recall.core.llm import build_llm_client
from recall.core.service import NoteService


def process_pending_notes() -> int:
    session = SessionLocal()
    try:
        service = NoteService(session=session, llm_client=build_llm_client(settings.llm_provider))
        processed = 0
        for note in service.claim_pending_notes(limit=settings.enrich_batch_size):
            try:
                if service.enrich_note(note.id) is not None:
                    processed += 1
            except Exception as exc:  # pragma: no cover - worker should keep going if one note fails
                service.record_enrichment_failure(note.id, str(exc))
        return processed
    finally:
        session.close()


def main() -> None:
    init_db()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(process_pending_notes, "interval", seconds=settings.enrich_interval_seconds, id="recall-enrichment")
    scheduler.start()
    process_pending_notes()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
