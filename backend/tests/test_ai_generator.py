"""Unit tests for AIGenerator"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from ai_generator import AIGenerator


@pytest.mark.unit
class TestAIGenerator:
    """Test cases for AIGenerator"""

    def test_init(self):
        """Test AIGenerator initialization"""
        api_key = "test-api-key"
        model = "claude-3-sonnet-20241022"

        generator = AIGenerator(api_key, model)

        assert generator.model == model
        assert generator.base_params["model"] == model
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800

    def test_generate_response_without_tools(
        self, mock_ai_generator, mock_anthropic_client, anthropic_text_response
    ):
        """Test generate_response without tools available"""
        mock_anthropic_client.messages.create.return_value = anthropic_text_response

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator.generate_response("Test query")

        # Verify API call
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args[1]

        assert (
            call_args["model"] == "claude-sonnet-4-20250514"
        )  # Updated model from ai_generator.py
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert call_args["messages"][0]["content"] == "Test query"
        assert "tools" not in call_args

        # Verify result
        assert result == "This is a test response"

        # Verify debug logging
        mock_print.assert_called_with("[DEBUG] No tools available for this query")

    def test_generate_response_with_tools_not_used(
        self,
        mock_ai_generator,
        mock_anthropic_client,
        anthropic_text_response,
        mock_tool_manager,
    ):
        """Test generate_response with tools available but not used"""
        mock_anthropic_client.messages.create.return_value = anthropic_text_response

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator.generate_response(
                "Test query", tools=tools, tool_manager=mock_tool_manager
            )

        # Verify API call includes tools
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == {"type": "auto"}

        # Verify result
        assert result == "This is a test response"

        # Verify debug logging shows round started and no tool use detected
        mock_print.assert_any_call("[DEBUG] Starting round 1/2")
        mock_print.assert_any_call("[DEBUG] No tool use in round 1, returning response")

    def test_generate_response_with_tool_use(
        self, mock_ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test generate_response when AI uses tools"""
        # Setup tool use response followed by final text response
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_block.id = "tool_123"
        tool_response.content = [tool_block]

        final_response = Mock()
        final_response.stop_reason = "stop"
        final_text = Mock()
        final_text.text = "Tool execution result"
        final_response.content = [final_text]

        mock_anthropic_client.messages.create.side_effect = [
            tool_response,
            final_response,
        ]
        mock_tool_manager.execute_tool.return_value = "Tool result"

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator.generate_response(
                "Test query", tools=tools, tool_manager=mock_tool_manager
            )

        # Verify tool execution was called
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test"
        )
        mock_print.assert_any_call("[DEBUG] Tool use detected in round 1")

        assert result == "Tool execution result"

    def test_generate_response_with_conversation_history(
        self, mock_ai_generator, mock_anthropic_client, anthropic_text_response
    ):
        """Test generate_response with conversation history"""
        mock_anthropic_client.messages.create.return_value = anthropic_text_response

        history = "Previous conversation context"
        result = mock_ai_generator.generate_response(
            "Test query", conversation_history=history
        )

        # Verify system prompt includes history
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert "Previous conversation:" in call_args["system"]
        assert history in call_args["system"]

    def test_handle_tool_execution(
        self, mock_ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test _handle_tool_execution method"""
        # Setup initial response with tool use
        initial_response = Mock()
        initial_response.content = [Mock()]
        initial_response.content[0].type = "tool_use"
        initial_response.content[0].name = "search_course_content"
        initial_response.content[0].input = {"query": "test"}
        initial_response.content[0].id = "tool_123"

        # Setup tool manager
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Setup final response
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Final AI response with tool results"
        mock_anthropic_client.messages.create.return_value = final_response

        base_params = {
            "messages": [{"role": "user", "content": "test query"}],
            "system": "test system prompt",
        }

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator._handle_tool_execution(
                initial_response, base_params, mock_tool_manager
            )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test"
        )

        # Verify debug logging
        mock_print.assert_any_call(
            "[DEBUG] Executing tool: search_course_content with params: {'query': 'test'}"
        )
        mock_print.assert_any_call("[DEBUG] Tool result length: 11 characters")
        mock_print.assert_any_call("[DEBUG] Final AI response length: 35 characters")

        # Verify final API call structure
        final_call_args = mock_anthropic_client.messages.create.call_args[1]
        assert (
            len(final_call_args["messages"]) == 3
        )  # user + assistant + user(tool_results)
        assert final_call_args["messages"][0]["role"] == "user"
        assert final_call_args["messages"][1]["role"] == "assistant"
        assert final_call_args["messages"][2]["role"] == "user"

        assert result == "Final AI response with tool results"

    def test_handle_tool_execution_multiple_tools(
        self, mock_ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test _handle_tool_execution with multiple tool calls"""
        # Setup initial response with multiple tool uses
        initial_response = Mock()
        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.name = "search_course_content"
        tool_block_1.input = {"query": "test1"}
        tool_block_1.id = "tool_123"

        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.name = "get_course_outline"
        tool_block_2.input = {"course_name": "test course"}
        tool_block_2.id = "tool_456"

        initial_response.content = [tool_block_1, tool_block_2]

        # Setup tool manager responses
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        # Setup final response
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Final response"
        mock_anthropic_client.messages.create.return_value = final_response

        base_params = {
            "messages": [{"role": "user", "content": "test query"}],
            "system": "test system prompt",
        }

        result = mock_ai_generator._handle_tool_execution(
            initial_response, base_params, mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="test1"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_name="test course"
        )

        # Verify final message has both tool results
        final_call_args = mock_anthropic_client.messages.create.call_args[1]
        tool_results_message = final_call_args["messages"][2]["content"]
        assert len(tool_results_message) == 2
        assert tool_results_message[0]["tool_use_id"] == "tool_123"
        assert tool_results_message[0]["content"] == "Result 1"
        assert tool_results_message[1]["tool_use_id"] == "tool_456"
        assert tool_results_message[1]["content"] == "Result 2"

    def test_handle_tool_execution_mixed_content(
        self, mock_ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test _handle_tool_execution with mixed content types"""
        # Setup initial response with text and tool use
        initial_response = Mock()
        text_block = Mock()
        text_block.type = "text"

        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_block.id = "tool_123"

        initial_response.content = [text_block, tool_block]

        # Setup tool manager
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Setup final response
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Final response"
        mock_anthropic_client.messages.create.return_value = final_response

        base_params = {
            "messages": [{"role": "user", "content": "test query"}],
            "system": "test system prompt",
        }

        result = mock_ai_generator._handle_tool_execution(
            initial_response, base_params, mock_tool_manager
        )

        # Verify only tool blocks were executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test"
        )

        # Verify result
        assert result == "Final response"

    def test_system_prompt_structure(self, mock_ai_generator):
        """Test that system prompt contains expected content"""
        system_prompt = mock_ai_generator.SYSTEM_PROMPT

        # Verify key components are present
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt
        assert "Tool Usage Guidelines" in system_prompt
        assert "Response Protocol" in system_prompt
        assert "preserve and include ALL course links" in system_prompt

    def test_base_params_structure(self, mock_ai_generator):
        """Test that base parameters are correctly structured"""
        params = mock_ai_generator.base_params

        assert params["model"] == "claude-sonnet-4-20250514"
        assert params["temperature"] == 0
        assert params["max_tokens"] == 800

    @patch("builtins.print")
    def test_debug_logging_levels(
        self,
        mock_print,
        mock_ai_generator,
        mock_anthropic_client,
        anthropic_text_response,
    ):
        """Test different debug logging scenarios"""
        mock_anthropic_client.messages.create.return_value = anthropic_text_response

        # Test without tools
        mock_ai_generator.generate_response("Test query")
        mock_print.assert_called_with("[DEBUG] No tools available for this query")

    def test_sequential_tool_calling_two_rounds(
        self,
        mock_ai_generator,
        mock_anthropic_client,
        anthropic_sequential_responses,
        mock_tool_manager,
    ):
        """Test sequential tool calling with two full rounds"""
        # Setup sequential responses: tool -> tool -> final
        mock_anthropic_client.messages.create.side_effect = (
            anthropic_sequential_responses
        )

        # Setup tool manager responses
        mock_tool_manager.execute_tool.side_effect = [
            "First tool result",
            "Second tool result",
        ]

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator.generate_response(
                "Test multi-round query", tools=tools, tool_manager=mock_tool_manager
            )

        # Verify two tool executions occurred
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="first search"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_name="test course"
        )

        # Verify 3 API calls were made (round 1, round 2, final)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify final result
        assert result == "Final synthesized response after two tool calls"

        # Verify debug logging shows round progression
        mock_print.assert_any_call("[DEBUG] Starting round 1/2")
        mock_print.assert_any_call("[DEBUG] Starting round 2/2")
        mock_print.assert_any_call(
            "[DEBUG] Max rounds reached, making final call without tools"
        )

    def test_sequential_tool_calling_early_termination(
        self,
        mock_ai_generator,
        mock_anthropic_client,
        anthropic_single_round_response,
        mock_tool_manager,
    ):
        """Test sequential tool calling that terminates after first round due to no tool use"""
        # Setup single round response: tool -> text (no more tools)
        mock_anthropic_client.messages.create.side_effect = (
            anthropic_single_round_response
        )

        mock_tool_manager.execute_tool.return_value = "Tool result"

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator.generate_response(
                "Test single-round query", tools=tools, tool_manager=mock_tool_manager
            )

        # Verify only one tool execution
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="single search"
        )

        # Verify 2 API calls (round 1 with tool, round 2 without tools)
        assert mock_anthropic_client.messages.create.call_count == 2

        # Verify result
        assert result == "Response after single tool call"

        # Verify debug logging
        mock_print.assert_any_call("[DEBUG] Starting round 1/2")
        mock_print.assert_any_call("[DEBUG] Starting round 2/2")
        mock_print.assert_any_call("[DEBUG] No tool use in round 2, returning response")

    def test_sequential_tool_calling_max_rounds_reached(
        self, mock_ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test that sequential tool calling terminates after max rounds"""
        # Setup responses that would continue indefinitely with tools
        tool_response_1 = Mock()
        tool_response_1.stop_reason = "tool_use"
        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.name = "search_course_content"
        tool_block_1.input = {"query": "search 1"}
        tool_block_1.id = "tool_1"
        tool_response_1.content = [tool_block_1]

        tool_response_2 = Mock()
        tool_response_2.stop_reason = "tool_use"
        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.name = "search_course_content"
        tool_block_2.input = {"query": "search 2"}
        tool_block_2.id = "tool_2"
        tool_response_2.content = [tool_block_2]

        final_response = Mock()
        final_response.stop_reason = "stop"
        final_text = Mock()
        final_text.text = "Final response after max rounds"
        final_response.content = [final_text]

        mock_anthropic_client.messages.create.side_effect = [
            tool_response_1,
            tool_response_2,
            final_response,
        ]
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator.generate_response(
                "Test max rounds query", tools=tools, tool_manager=mock_tool_manager
            )

        # Verify exactly 2 tool executions (max rounds)
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify 3 API calls total (2 rounds + final)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify final call doesn't include tools
        final_call_args = mock_anthropic_client.messages.create.call_args_list[2][1]
        assert "tools" not in final_call_args

        assert result == "Final response after max rounds"
        mock_print.assert_any_call(
            "[DEBUG] Max rounds reached, making final call without tools"
        )

    def test_sequential_tool_calling_tool_execution_error(
        self,
        mock_ai_generator,
        mock_anthropic_client,
        anthropic_tool_use_response,
        mock_tool_manager,
    ):
        """Test sequential tool calling when tool execution fails"""
        mock_anthropic_client.messages.create.return_value = anthropic_tool_use_response

        # Simulate tool execution error
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        with patch("builtins.print") as mock_print:
            result = mock_ai_generator.generate_response(
                "Test error query", tools=tools, tool_manager=mock_tool_manager
            )

        # Verify tool was attempted
        mock_tool_manager.execute_tool.assert_called_once()

        # Verify error handling
        assert (
            result
            == "I encountered an error while searching for information. Please try rephrasing your question."
        )
        mock_print.assert_any_call("[DEBUG] Tool execution failed in round 1")

    def test_sequential_tool_calling_no_tools_immediate_response(
        self, mock_ai_generator, mock_anthropic_client, anthropic_text_response
    ):
        """Test that queries without tool use return immediately"""
        mock_anthropic_client.messages.create.return_value = anthropic_text_response

        # Response that doesn't use tools
        response = mock_ai_generator.generate_response("What is 2+2?")

        # Verify single API call
        assert mock_anthropic_client.messages.create.call_count == 1

        # Verify response
        assert response == "This is a test response"

    def test_backward_compatibility_with_handle_tool_execution(
        self,
        mock_ai_generator,
        mock_anthropic_client,
        anthropic_tool_use_response,
        mock_tool_manager,
    ):
        """Test that _handle_tool_execution still works for backward compatibility"""
        mock_tool_manager.execute_tool.return_value = "Legacy tool result"

        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Legacy final response"
        mock_anthropic_client.messages.create.return_value = final_response

        base_params = {
            "messages": [{"role": "user", "content": "test query"}],
            "system": "test system prompt",
        }

        with patch("builtins.print"):
            result = mock_ai_generator._handle_tool_execution(
                anthropic_tool_use_response, base_params, mock_tool_manager
            )

        # Verify tool execution
        mock_tool_manager.execute_tool.assert_called_once()

        # Verify result
        assert result == "Legacy final response"
