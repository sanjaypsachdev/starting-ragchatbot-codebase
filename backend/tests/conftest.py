import sys
import os
from unittest.mock import MagicMock

# Add backend/ to path so tests can import backend modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
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
