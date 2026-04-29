# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

Always use `uv` for running Python and managing dependencies — never `pip` directly.

```bash
# Install / sync dependencies
uv sync

# Add a new dependency
uv add <package>

# Quick start
./run.sh

# Manual start (from repo root)
cd backend && uv run uvicorn app:app --reload --port 8000
```

Requires a `.env` file at the repo root with `ANTHROPIC_API_KEY=...`. The app serves both the API and the frontend at `http://localhost:8000`. API docs at `/docs`.

## Architecture

This is a RAG chatbot that answers questions about course materials. The backend is FastAPI; the frontend is plain HTML/CSS/JS served as static files from the same server.

**Request flow:**

1. Browser POSTs `{query, session_id}` to `POST /api/query`
2. `RAGSystem.query()` fetches conversation history from `SessionManager`, then calls `AIGenerator`
3. `AIGenerator` makes a first Claude API call with the `search_course_content` tool available. Claude either answers directly or calls the tool.
4. If the tool is called, `CourseSearchTool` → `VectorStore.search()` embeds the query and retrieves up to 5 chunks from ChromaDB, then a second Claude API call synthesizes the chunks into a final answer.
5. Sources and the answer are returned; `SessionManager` records the exchange (capped at 2 exchanges).

**Component responsibilities:**

- `backend/rag_system.py` — central orchestrator; the only entry point for queries and document ingestion
- `backend/ai_generator.py` — all Claude API calls live here; handles the two-turn tool-use loop
- `backend/vector_store.py` — ChromaDB wrapper with two collections: `course_catalog` (one doc per course) and `course_content` (chunked text). Course title is the document ID in `course_catalog`.
- `backend/search_tools.py` — `Tool` ABC, `CourseSearchTool` implementation, and `ToolManager` registry. Adding a new tool means subclassing `Tool` and calling `tool_manager.register_tool()`.
- `backend/document_processor.py` — parses `.txt` course files and chunks them (800 char chunks, 100 char overlap, sentence-aware splitting)
- `backend/session_manager.py` — in-memory sessions only; sessions are lost on restart
- `backend/config.py` — all tunable parameters (model, chunk size, overlap, max results, history length)

**Document format** (files in `/docs/`):
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<lesson content...>

Lesson 1: <title>
...
```
Documents are loaded at startup from `../docs/` relative to the backend. Already-indexed courses (matched by title) are skipped.

## Key Design Decisions

- **Tool-based retrieval**: Claude autonomously decides whether to search. General knowledge questions skip ChromaDB entirely.
- **Two-turn Claude loop**: first call includes tools; if a tool is used, a second call (without tools) synthesizes the retrieved context into the final answer.
- **Semantic course name resolution**: `VectorStore._resolve_course_name()` uses vector similarity to match partial/fuzzy course names before filtering `course_content`.
- **No persistent sessions**: `SessionManager` is in-memory. There is no database-backed session store.
- **Embeddings**: `all-MiniLM-L6-v2` via `sentence-transformers`, run locally through ChromaDB's embedding function wrapper.
