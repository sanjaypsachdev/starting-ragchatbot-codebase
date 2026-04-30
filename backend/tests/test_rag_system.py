"""Tests for RAGSystem.query(): orchestration, source handling, and session updates."""
import pytest
from unittest.mock import MagicMock, patch
from rag_system import RAGSystem
from config import Config


def _make_rag_system():
    """Build a RAGSystem with all heavy components mocked out."""
    cfg = Config(ANTHROPIC_API_KEY="test-key")

    with (
        patch("rag_system.DocumentProcessor"),
        patch("rag_system.VectorStore"),
        patch("rag_system.AIGenerator") as MockAI,
        patch("rag_system.SessionManager") as MockSession,
        patch("rag_system.ToolManager") as MockTM,
        patch("rag_system.CourseSearchTool"),
        patch("rag_system.CourseOutlineTool"),
    ):
        rag = RAGSystem(cfg)

    # Re-wire mocks so we can control them in tests
    mock_ai = MagicMock()
    mock_ai.generate_response.return_value = "Here is the answer."
    rag.ai_generator = mock_ai

    mock_session = MagicMock()
    mock_session.get_conversation_history.return_value = None
    rag.session_manager = mock_session

    mock_tm = MagicMock()
    mock_tm.get_tool_definitions.return_value = [{"name": "search_course_content"}]
    mock_tm.get_last_sources.return_value = [{"label": "Course - Lesson 1", "url": "https://example.com"}]
    rag.tool_manager = mock_tm

    return rag, mock_ai, mock_session, mock_tm


class TestRAGSystemQuery:
    def test_query_calls_ai_generator_once(self):
        rag, mock_ai, _, _ = _make_rag_system()

        rag.query("What is RAG?")

        mock_ai.generate_response.assert_called_once()

    def test_query_passes_tool_definitions_to_ai(self):
        rag, mock_ai, _, mock_tm = _make_rag_system()

        rag.query("What is RAG?")

        call_kwargs = mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["tools"] == mock_tm.get_tool_definitions.return_value

    def test_query_passes_tool_manager_to_ai(self):
        rag, mock_ai, _, mock_tm = _make_rag_system()

        rag.query("What is RAG?")

        call_kwargs = mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["tool_manager"] is mock_tm

    def test_query_returns_answer_from_ai_generator(self):
        rag, mock_ai, _, _ = _make_rag_system()
        mock_ai.generate_response.return_value = "The answer is 42."

        answer, _ = rag.query("What is the answer?")

        assert answer == "The answer is 42."

    def test_query_returns_sources_from_tool_manager(self):
        rag, _, _, mock_tm = _make_rag_system()
        expected_sources = [{"label": "Course A - Lesson 3", "url": "https://example.com/3"}]
        mock_tm.get_last_sources.return_value = expected_sources

        _, sources = rag.query("What is prompt engineering?")

        assert sources == expected_sources

    def test_query_resets_sources_after_retrieval(self):
        rag, _, _, mock_tm = _make_rag_system()

        rag.query("Any question")

        mock_tm.reset_sources.assert_called_once()

    def test_query_records_exchange_in_session(self):
        rag, mock_ai, mock_session, _ = _make_rag_system()
        mock_ai.generate_response.return_value = "The answer."

        rag.query("My question", session_id="session_1")

        mock_session.add_exchange.assert_called_once_with("session_1", "My question", "The answer.")

    def test_query_without_session_skips_history_lookup(self):
        rag, _, mock_session, _ = _make_rag_system()

        rag.query("A question")  # no session_id

        mock_session.get_conversation_history.assert_not_called()

    def test_query_with_session_fetches_history(self):
        rag, mock_ai, mock_session, _ = _make_rag_system()
        mock_session.get_conversation_history.return_value = "User: Hi\nAssistant: Hello!"

        rag.query("Follow-up", session_id="session_2")

        mock_session.get_conversation_history.assert_called_once_with("session_2")
        call_kwargs = mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] == "User: Hi\nAssistant: Hello!"

    def test_query_propagates_ai_generator_exception(self):
        rag, mock_ai, _, _ = _make_rag_system()
        mock_ai.generate_response.side_effect = RuntimeError("API call failed")

        with pytest.raises(RuntimeError, match="API call failed"):
            rag.query("This should raise")
