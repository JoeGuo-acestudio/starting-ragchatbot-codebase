import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **search_course_content** - For finding specific content within courses
2. **get_course_outline** - For course structure, lesson lists, and navigation information

Tool Usage Guidelines:
- Use **search_course_content** for questions about specific course content or detailed educational materials
- Use **get_course_outline** for questions about course structure, lesson organization, navigation, or when users want to see what's available in a course
- **Up to 2 tool calls maximum per query** - use them strategically
- You may perform a second search to refine or expand on initial results if needed
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course content questions**: Use search_course_content first, then answer
- **Course structure/outline questions**: Use get_course_outline first, then answer
- **Follow-up searches**: If initial results are incomplete, perform one additional targeted search
- **IMPORTANT**: When using get_course_outline, ALWAYS preserve and include ALL course links and lesson links from the tool output. Never summarize or omit clickable links.
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the course outline"

All responses must be:
1. **Complete and accurate** - Include all relevant information from tools, especially links
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Link-preserving** - Always include course and lesson links when available
Provide only the direct answer to what was asked, but ensure course outlines include all links.
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
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Execute up to 2 rounds of tool calls if tools are available
        if tools and tool_manager:
            return self._execute_sequential_rounds(api_params, tool_manager, max_rounds=2)
        
        # No tools available - make direct API call
        response = self.client.messages.create(**api_params)
        print(f"[DEBUG] No tools available for this query")
        return response.content[0].text
    
    def _execute_sequential_rounds(self, api_params: Dict[str, Any], tool_manager, max_rounds: int = 2) -> str:
        """
        Execute up to max_rounds of sequential API calls with tool usage.
        
        Args:
            api_params: Initial API parameters
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of rounds (default 2)
            
        Returns:
            Final response text
        """
        messages = api_params["messages"].copy()
        current_round = 0
        
        while current_round < max_rounds:
            current_round += 1
            print(f"[DEBUG] Starting round {current_round}/{max_rounds}")
            
            # Prepare API call with current messages
            round_params = {
                **api_params,
                "messages": messages
            }
            
            # Get response from Claude
            response = self.client.messages.create(**round_params)
            
            # Check for tool usage
            if response.stop_reason == "tool_use" and tool_manager:
                print(f"[DEBUG] Tool use detected in round {current_round}")
                
                # Add Claude's tool use response to messages
                messages.append({"role": "assistant", "content": response.content})
                
                # Execute tools and add results
                tool_results = self._execute_tools(response, tool_manager)
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                    
                    # Continue to next round if we haven't hit the limit
                    if current_round < max_rounds:
                        continue
                    else:
                        # Final round - make one more call without tools to get response
                        print(f"[DEBUG] Max rounds reached, making final call without tools")
                        return self._make_final_call(messages, api_params)
                else:
                    # Tool execution failed
                    print(f"[DEBUG] Tool execution failed in round {current_round}")
                    return "I encountered an error while searching for information. Please try rephrasing your question."
            else:
                # No tools used or no tool manager - return response
                print(f"[DEBUG] No tool use in round {current_round}, returning response")
                return response.content[0].text
        
        # Should not reach here, but fallback
        return "I was unable to generate a complete response."
    
    def _execute_tools(self, response, tool_manager):
        """
        Execute all tool calls in a response and return results.
        
        Args:
            response: Claude response containing tool use
            tool_manager: Manager to execute tools
            
        Returns:
            List of tool results or None if execution fails
        """
        tool_results = []
        
        try:
            for content_block in response.content:
                if content_block.type == "tool_use":
                    print(f"[DEBUG] Executing tool: {content_block.name} with params: {content_block.input}")
                    
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **content_block.input
                    )
                    
                    print(f"[DEBUG] Tool result length: {len(str(tool_result))} characters")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
            
            return tool_results if tool_results else None
            
        except Exception as e:
            print(f"[DEBUG] Tool execution error: {e}")
            return None
    
    def _make_final_call(self, messages: List[Dict], original_params: Dict[str, Any]) -> str:
        """
        Make final API call without tools to get Claude's synthesized response.
        
        Args:
            messages: Current conversation messages
            original_params: Original API parameters for system prompt
            
        Returns:
            Final response text
        """
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": original_params["system"]
            # Note: No tools included in final call
        }
        
        try:
            final_response = self.client.messages.create(**final_params)
            final_result = final_response.content[0].text
            print(f"[DEBUG] Final response length: {len(final_result)} characters")
            return final_result
            
        except Exception as e:
            print(f"[DEBUG] Final API call error: {e}")
            return "I encountered an error while generating the final response."
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                print(f"[DEBUG] Executing tool: {content_block.name} with params: {content_block.input}")
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                print(f"[DEBUG] Tool result length: {len(str(tool_result))} characters")
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        final_result = final_response.content[0].text
        print(f"[DEBUG] Final AI response length: {len(final_result)} characters")
        return final_result