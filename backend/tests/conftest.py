import sys
import os
from unittest.mock import MagicMock
from typing import List, Optional

# Add backend/ to path so tests can import backend modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from vector_store import SearchResults, VectorStore
from search_tools import ToolManager


@pytest.fixture
def sample_search_results():
    """Two-document SearchResults with realistic metadata."""
    return SearchResults(
        documents=[
            "Claude is a helpful AI assistant built by Anthropic.",
            "Prompt engineering involves crafting effective instructions for AI models.",
        ],
        metadata=[
            {"course_title": "Intro to Claude", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Intro to Claude", "lesson_number": 2, "chunk_index": 0},
        ],
        distances=[0.15, 0.22],
    )


@pytest.fixture
def empty_search_results():
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    return SearchResults(
        documents=[], metadata=[], distances=[], error="Search error: collection is empty"
    )


@pytest.fixture
def mock_vector_store(sample_search_results):
    store = MagicMock(spec=VectorStore)
    store.search.return_value = sample_search_results
    store.get_lesson_link.return_value = "https://example.com/course/lesson/1"
    return store


@pytest.fixture
def mock_tool_manager():
    manager = MagicMock(spec=ToolManager)
    manager.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        }
    ]
    manager.execute_tool.return_value = "Relevant course content found."
    manager.get_last_sources.return_value = [{"label": "Intro to Claude - Lesson 1", "url": "https://example.com"}]
    return manager


def _make_text_block(text: str):
    """Return a minimal object resembling anthropic TextBlock."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(tool_name: str, tool_id: str, inputs: dict):
    """Return a minimal object resembling anthropic ToolUseBlock."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = tool_id
    block.input = inputs
    return block


def _make_claude_response(stop_reason: str, content_blocks: list):
    """Factory: build a fake anthropic Message object."""
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    return response


@pytest.fixture
def make_claude_response():
    return _make_claude_response


@pytest.fixture
def make_text_block():
    return _make_text_block


@pytest.fixture
def make_tool_use_block():
    return _make_tool_use_block


# ---------------------------------------------------------------------------
# API test fixtures
# ---------------------------------------------------------------------------

class _QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class _QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    session_id: str


class _CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


@pytest.fixture
def mock_rag_system():
    """MagicMock of RAGSystem with realistic default return values."""
    rag = MagicMock()
    rag.query.return_value = (
        "Here is the answer.",
        [{"label": "Intro to Claude - Lesson 1", "url": "https://example.com/lesson/1"}],
    )
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Intro to Claude", "Advanced Prompting"],
    }
    rag.session_manager.create_session.return_value = "session-generated"
    rag.session_manager.sessions = {}
    return rag


@pytest.fixture
def client(mock_rag_system):
    """TestClient wired to a minimal FastAPI app that mirrors app.py's API routes.

    Defined inline to avoid the static-file mount in app.py that requires
    ../frontend to exist on disk.
    """
    test_app = FastAPI()

    @test_app.post("/api/query", response_model=_QueryResponse)
    async def query_documents(request: _QueryRequest):
        try:
            session_id = request.session_id or mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            return _QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=_CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return _CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        mock_rag_system.session_manager.sessions.pop(session_id, None)
        return {"deleted": True}

    return TestClient(test_app)
