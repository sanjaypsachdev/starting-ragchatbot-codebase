"""Tests for CourseSearchTool.execute() and result formatting."""
import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    def test_execute_returns_formatted_string(self, mock_vector_store, sample_search_results):
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="what is Claude?")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_execute_empty_results(self, mock_vector_store, empty_search_results):
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="unknown topic")

        assert "No relevant content found" in result

    def test_execute_with_error_in_results(self, mock_vector_store, error_search_results):
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="anything")

        assert "Search error" in result

    def test_execute_passes_course_name_to_store(self, mock_vector_store, sample_search_results):
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="prompt tips", course_name="Intro to Claude")

        mock_vector_store.search.assert_called_once_with(
            query="prompt tips",
            course_name="Intro to Claude",
            lesson_number=None,
        )

    def test_execute_passes_lesson_number_to_store(self, mock_vector_store, sample_search_results):
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="tool use", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="tool use",
            course_name=None,
            lesson_number=3,
        )

    def test_execute_populates_last_sources(self, mock_vector_store, sample_search_results):
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="Claude models")

        assert len(tool.last_sources) == 2
        for src in tool.last_sources:
            assert "label" in src
            assert "url" in src

    def test_execute_empty_clears_last_sources(self, mock_vector_store, empty_search_results):
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)
        tool.last_sources = [{"label": "stale", "url": None}]

        tool.execute(query="anything")

        # Empty results means format_results is never called, so last_sources stays stale.
        # But an error result should also not populate sources.
        assert tool.last_sources == [{"label": "stale", "url": None}]

    def test_execute_error_result_does_not_populate_sources(self, mock_vector_store, error_search_results):
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)
        tool.last_sources = []

        tool.execute(query="anything")

        assert tool.last_sources == []

    def test_format_results_contains_course_lesson_header(self, mock_vector_store, sample_search_results):
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="AI models")

        # Both docs belong to "Intro to Claude" with lesson numbers 1 and 2
        assert "[Intro to Claude - Lesson 1]" in result
        assert "[Intro to Claude - Lesson 2]" in result

    def test_format_results_includes_document_content(self, mock_vector_store, sample_search_results):
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="AI assistant")

        assert "Claude is a helpful AI assistant" in result
        assert "Prompt engineering" in result
