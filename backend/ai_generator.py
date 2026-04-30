import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Up to 2 sequential tool calls per query** — use a second call only when the first result is insufficient or you need different information to answer fully (e.g., get an outline first, then search specific content)
- Prefer a single tool call when one result is sufficient
- Do not call the same tool with identical arguments twice
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.

Course Outline Tool Usage:
- Use the outline tool for questions about course structure, lesson list, available lessons, or course overview
- The outline tool returns the course title, course link, and every lesson with its number and title
- Present the course link and all lesson numbers/titles exactly as returned — do not paraphrase or omit lessons
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        messages = [{"role": "user", "content": query}]
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution loop if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._run_tool_loop(response, messages, system_content, tools, tool_manager)

        # Return direct response
        return response.content[0].text

    def _run_tool_loop(self, initial_response, messages: List, system_content: str,
                       tools: List, tool_manager) -> str:
        """
        Execute up to MAX_TOOL_ROUNDS of tool calls, with Claude reasoning between rounds.

        Each intermediate round is called with tools so Claude can chain another call.
        The final round (or early exit) produces the synthesized text answer.
        """
        current_response = initial_response

        for round_num in range(self.MAX_TOOL_ROUNDS):
            # Append Claude's tool-use response to message history
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls in this round
            tool_results = []
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })

            messages.append({"role": "user", "content": tool_results})

            is_last_round = (round_num == self.MAX_TOOL_ROUNDS - 1)

            if is_last_round:
                # Forced synthesis: strip tools so Claude must answer directly
                final_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": system_content
                }
                final_response = self.client.messages.create(**final_params)
                return final_response.content[0].text
            else:
                # Intermediate: offer tools so Claude can chain another call if needed
                loop_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": system_content,
                    "tools": tools,
                    "tool_choice": {"type": "auto"}
                }
                current_response = self.client.messages.create(**loop_params)

                if current_response.stop_reason != "tool_use":
                    # Claude answered directly without calling another tool
                    return current_response.content[0].text

        # Unreachable with MAX_TOOL_ROUNDS >= 1, defensive fallback
        return current_response.content[0].text
