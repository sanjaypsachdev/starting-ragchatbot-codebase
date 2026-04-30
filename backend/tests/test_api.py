"""Tests for FastAPI endpoint request/response handling."""
import pytest


class TestQueryEndpoint:
    def test_query_returns_200_with_answer_and_sources(self, client):
        response = client.post("/api/query", json={"query": "What is RAG?"})

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Here is the answer."
        assert isinstance(body["sources"], list)
        assert len(body["sources"]) == 1

    def test_query_response_contains_session_id(self, client):
        response = client.post("/api/query", json={"query": "What is RAG?"})

        assert "session_id" in response.json()

    def test_query_auto_generates_session_id_when_omitted(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Any question"})

        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_uses_provided_session_id(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Follow-up", "session_id": "session-existing"})

        mock_rag_system.session_manager.create_session.assert_not_called()
        call_args = mock_rag_system.query.call_args
        assert call_args.args[1] == "session-existing"

    def test_query_auto_generated_session_id_in_response(self, client, mock_rag_system):
        mock_rag_system.session_manager.create_session.return_value = "session-new"

        response = client.post("/api/query", json={"query": "New conversation"})

        assert response.json()["session_id"] == "session-new"

    def test_query_provided_session_id_echoed_in_response(self, client):
        response = client.post(
            "/api/query", json={"query": "Hello", "session_id": "session-abc"}
        )

        assert response.json()["session_id"] == "session-abc"

    def test_query_passes_query_text_to_rag_system(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Explain embeddings"})

        call_args = mock_rag_system.query.call_args
        assert call_args.args[0] == "Explain embeddings"

    def test_query_returns_500_when_rag_raises(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("vector store unavailable")

        response = client.post("/api/query", json={"query": "Failing query"})

        assert response.status_code == 500
        assert "vector store unavailable" in response.json()["detail"]

    def test_query_sources_have_label_and_url(self, client, mock_rag_system):
        mock_rag_system.query.return_value = (
            "Answer.",
            [{"label": "Course A - Lesson 2", "url": "https://example.com/2"}],
        )

        response = client.post("/api/query", json={"query": "What is prompting?"})

        source = response.json()["sources"][0]
        assert "label" in source
        assert "url" in source


class TestCoursesEndpoint:
    def test_courses_returns_200(self, client):
        response = client.get("/api/courses")

        assert response.status_code == 200

    def test_courses_returns_total_count(self, client):
        response = client.get("/api/courses")

        assert response.json()["total_courses"] == 2

    def test_courses_returns_course_titles_list(self, client):
        response = client.get("/api/courses")

        titles = response.json()["course_titles"]
        assert isinstance(titles, list)
        assert "Intro to Claude" in titles
        assert "Advanced Prompting" in titles

    def test_courses_returns_500_when_analytics_raises(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("db error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "db error" in response.json()["detail"]


class TestDeleteSessionEndpoint:
    def test_delete_session_returns_200(self, client):
        response = client.delete("/api/session/session-123")

        assert response.status_code == 200

    def test_delete_session_returns_deleted_true(self, client):
        response = client.delete("/api/session/session-123")

        assert response.json() == {"deleted": True}

    def test_delete_session_removes_from_sessions(self, client, mock_rag_system):
        mock_rag_system.session_manager.sessions = {"session-abc": []}

        client.delete("/api/session/session-abc")

        assert "session-abc" not in mock_rag_system.session_manager.sessions

    def test_delete_nonexistent_session_still_returns_deleted(self, client, mock_rag_system):
        mock_rag_system.session_manager.sessions = {}

        response = client.delete("/api/session/does-not-exist")

        assert response.status_code == 200
        assert response.json()["deleted"] is True
