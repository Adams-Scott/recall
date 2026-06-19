# Recall

Recall is a local-first note-taking app for small, easy-to-forget notes.

The first implementation uses:

- Python and FastAPI for the API and web UI
- SQLite for local persistence
- A scheduled worker that enriches pending notes with elaboration and tags
- Docker Compose for local deployment

## Services

- API server: CRUD, search, and bot control endpoints
- Web interface: browser-based note management
- Worker: scheduled enrichment of unprocessed notes

## Run locally

1. Build and start the stack with Docker Compose.
2. Open the web interface on port 8001.
3. Use the API on port 8000 for JSON access.

## Notes

- The original note is preserved.
- Enrichment output is stored separately from the source note.
- Search scans the original note, elaboration, and tags.
