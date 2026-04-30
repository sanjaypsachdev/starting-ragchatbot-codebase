"""Tests for AIGenerator: model config, tool loop, and message formatting."""
import pytest
from unittest.mock import MagicMock, patch, call
from ai_generator import AIGenerator
from config import config

# Known-valid Anthropic model IDs as of Claude 4.x family
VALID_MODEL_IDS = {
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
}


class TestModelConfig:
    def test_model_name_is_valid(self):
        """Fails when config uses a retired or non-existent model ID."""
        assert config.ANTHROPIC_MODEL in VALID_MODEL_IDS, (
            f"config.ANTHROPIC_MODEL='{config.ANTHROPIC_MODEL}' is not a known-valid model. "
            f"Valid IDs: {VALID_MODEL_IDS}"
        )


class TestDirectResponse:
    def test_direct_response_returns_text(self, make_claude_response, make_text_block):
        text_block = make_text_block("Here is the answer.")
        fake_response = make_claude_response("end_turn", [text_block])

        with patch("anthropic.Anthropic") as MockAnthropic:
            MockAnthropic.return_value.messages.create.return_value = fake_response
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            result = gen.generate_response(query="What is Claude?")

        assert result == "Here is the answer."

    def test_direct_response_no_tools_arg_omits_tools(self, make_claude_response, make_text_block):
        fake_response = make_claude_response("end_turn", [make_text_block("Direct answer.")])

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.return_value = fake_response
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(query="What is 2+2?")

        call_kwargs = create.call_args.kwargs
        assert "tools" not in call_kwargs


class TestToolPassthrough:
    def test_tools_are_passed_when_provided(self, make_claude_response, make_text_block):
        fake_tools = [{"name": "search_course_content", "description": "search", "input_schema": {}}]
        fake_response = make_claude_response("end_turn", [make_text_block("Answer.")])

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.return_value = fake_response
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(query="What is MCP?", tools=fake_tools, tool_manager=MagicMock())

        call_kwargs = create.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == fake_tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_tool_use_stop_reason_triggers_second_api_call(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block = make_tool_use_block("search_course_content", "tool-id-1", {"query": "MCP"})
        first_response = make_claude_response("tool_use", [tool_block])
        second_response = make_claude_response("end_turn", [make_text_block("Final answer.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Relevant content about MCP."

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [first_response, second_response]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            result = gen.generate_response(
                query="What is MCP?",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        assert create.call_count == 2
        assert result == "Final answer."

    def test_tool_manager_execute_called_with_correct_args(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block = make_tool_use_block("search_course_content", "tool-id-2", {"query": "embeddings"})
        first_response = make_claude_response("tool_use", [tool_block])
        second_response = make_claude_response("end_turn", [make_text_block("Done.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Found content."

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [first_response, second_response]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(
                query="Explain embeddings",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="embeddings"
        )

    def test_tool_result_message_has_correct_format(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block = make_tool_use_block("search_course_content", "abc-123", {"query": "RAG"})
        first_response = make_claude_response("tool_use", [tool_block])
        second_response = make_claude_response("end_turn", [make_text_block("Answer.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "RAG content here."

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [first_response, second_response]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(
                query="Explain RAG",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        # Inspect second call's messages for the tool_result block
        second_call_kwargs = create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]
        # Last user message should contain the tool results
        tool_result_msg = messages[-1]
        assert tool_result_msg["role"] == "user"
        assert isinstance(tool_result_msg["content"], list)
        tr = tool_result_msg["content"][0]
        assert tr["type"] == "tool_result"
        assert tr["tool_use_id"] == "abc-123"
        assert tr["content"] == "RAG content here."

    def test_final_api_call_has_no_tools(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        # Two tool rounds: the 3rd (synthesis) call must have no tools
        tool_block_1 = make_tool_use_block("search_course_content", "id-1", {"query": "test"})
        tool_block_2 = make_tool_use_block("search_course_content", "id-2", {"query": "test2"})
        first_response = make_claude_response("tool_use", [tool_block_1])
        second_response = make_claude_response("tool_use", [tool_block_2])
        third_response = make_claude_response("end_turn", [make_text_block("Done.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "content."

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [first_response, second_response, third_response]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(
                query="test query",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        third_call_kwargs = create.call_args_list[2].kwargs
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_conversation_history_injected_into_system_prompt(
        self, make_claude_response, make_text_block
    ):
        fake_response = make_claude_response("end_turn", [make_text_block("Reply.")])
        history = "User: Hello\nAssistant: Hi there!"

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.return_value = fake_response
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(query="Follow-up question", conversation_history=history)

        call_kwargs = create.call_args.kwargs
        assert history in call_kwargs["system"]


class TestSequentialToolCalling:
    def test_two_round_flow_makes_three_api_calls(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block_1 = make_tool_use_block("search_course_content", "id-r0", {"query": "outline"})
        tool_block_2 = make_tool_use_block("search_course_content", "id-r1", {"query": "topic"})
        r0 = make_claude_response("tool_use", [tool_block_1])
        r1 = make_claude_response("tool_use", [tool_block_2])
        r_final = make_claude_response("end_turn", [make_text_block("Complete answer.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "search result"

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [r0, r1, r_final]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            result = gen.generate_response(
                query="Multi-step query",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        assert create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2
        assert result == "Complete answer."

    def test_early_exit_after_round_0_makes_two_api_calls(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block = make_tool_use_block("search_course_content", "id-r0", {"query": "topic"})
        r0 = make_claude_response("tool_use", [tool_block])
        r1 = make_claude_response("end_turn", [make_text_block("One-round answer.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "search result"

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [r0, r1]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            result = gen.generate_response(
                query="Simple query",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        assert create.call_count == 2
        assert mock_tool_manager.execute_tool.call_count == 1
        assert result == "One-round answer."

    def test_max_rounds_respected(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        # Provide more tool_use responses than MAX_TOOL_ROUNDS to confirm the loop stops
        tool_block_1 = make_tool_use_block("search_course_content", "id-r0", {"query": "a"})
        tool_block_2 = make_tool_use_block("search_course_content", "id-r1", {"query": "b"})
        r0 = make_claude_response("tool_use", [tool_block_1])
        r1 = make_claude_response("tool_use", [tool_block_2])
        r_final = make_claude_response("end_turn", [make_text_block("Synthesis.")])
        extra = make_claude_response("tool_use", [tool_block_1])  # must never be consumed

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "data"

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [r0, r1, r_final, extra]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(
                query="Complex query",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        assert create.call_count == 3  # never reaches the 4th (extra)

    def test_tool_error_passed_as_tool_result_content(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block = make_tool_use_block("search_course_content", "err-id", {"query": "q"})
        r0 = make_claude_response("tool_use", [tool_block])
        r1 = make_claude_response("end_turn", [make_text_block("Graceful answer.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = RuntimeError("index unavailable")

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [r0, r1]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            result = gen.generate_response(
                query="Query with broken tool",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        # No exception propagated
        assert result == "Graceful answer."
        # Second call's messages carry the error as a tool_result
        second_call_messages = create.call_args_list[1].kwargs["messages"]
        tool_result_msg = second_call_messages[-1]
        assert tool_result_msg["role"] == "user"
        tr = tool_result_msg["content"][0]
        assert tr["type"] == "tool_result"
        assert tr["tool_use_id"] == "err-id"
        assert tr["is_error"] is True
        assert "index unavailable" in tr["content"]

    def test_intermediate_round_includes_tools(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block = make_tool_use_block("search_course_content", "id-r0", {"query": "q"})
        r0 = make_claude_response("tool_use", [tool_block])
        r1 = make_claude_response("end_turn", [make_text_block("Answer.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "data"
        fake_tools = [{"name": "search_course_content"}]

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [r0, r1]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(query="q", tools=fake_tools, tool_manager=mock_tool_manager)

        second_call_kwargs = create.call_args_list[1].kwargs
        assert "tools" in second_call_kwargs
        assert "tool_choice" in second_call_kwargs

    def test_last_round_synthesis_omits_tools(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block_1 = make_tool_use_block("search_course_content", "id-r0", {"query": "a"})
        tool_block_2 = make_tool_use_block("search_course_content", "id-r1", {"query": "b"})
        r0 = make_claude_response("tool_use", [tool_block_1])
        r1 = make_claude_response("tool_use", [tool_block_2])
        r_final = make_claude_response("end_turn", [make_text_block("Final.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "data"

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [r0, r1, r_final]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(
                query="q",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        third_call_kwargs = create.call_args_list[2].kwargs
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_second_round_messages_include_first_round_results(
        self, make_claude_response, make_text_block, make_tool_use_block
    ):
        tool_block_1 = make_tool_use_block("search_course_content", "id-r0", {"query": "a"})
        tool_block_2 = make_tool_use_block("search_course_content", "id-r1", {"query": "b"})
        r0 = make_claude_response("tool_use", [tool_block_1])
        r1 = make_claude_response("tool_use", [tool_block_2])
        r_final = make_claude_response("end_turn", [make_text_block("Final.")])

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result data"

        with patch("anthropic.Anthropic") as MockAnthropic:
            create = MockAnthropic.return_value.messages.create
            create.side_effect = [r0, r1, r_final]
            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            gen.generate_response(
                query="Multi-step",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

        # The synthesis call (3rd) receives all 5 accumulated messages
        synthesis_messages = create.call_args_list[2].kwargs["messages"]
        assert len(synthesis_messages) == 5
        assert synthesis_messages[0]["role"] == "user"       # original query
        assert synthesis_messages[1]["role"] == "assistant"  # round-0 tool_use
        assert synthesis_messages[2]["role"] == "user"       # round-0 tool_results
        assert synthesis_messages[3]["role"] == "assistant"  # round-1 tool_use
        assert synthesis_messages[4]["role"] == "user"       # round-1 tool_results
        # round-0 tool result is present in the synthesis call's history
        round0_results = synthesis_messages[2]["content"]
        assert round0_results[0]["tool_use_id"] == "id-r0"
        assert round0_results[0]["content"] == "result data"
