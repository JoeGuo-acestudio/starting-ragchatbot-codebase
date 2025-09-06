"""Test fixtures and configuration for the test suite"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any
import tempfile
import os

from vector_store import SearchResults, VectorStore
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from ai_generator import AIGenerator
from rag_system import RAGSystem
from models import Course, Lesson, CourseChunk
from config import Config


# Sample test data
@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    lessons = [
        Lesson(
            lesson_number=1,
            title="Introduction to AI",
            lesson_link="https://example.com/lesson1"
        ),
        Lesson(
            lesson_number=2,
            title="Machine Learning Basics",
            lesson_link="https://example.com/lesson2"
        )
    ]
    return Course(
        title="AI Fundamentals",
        course_link="https://example.com/course",
        instructor="Dr. Smith",
        lessons=lessons
    )


@pytest.fixture
def sample_course_chunks():
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="Introduction to artificial intelligence and its applications.",
            course_title="AI Fundamentals",
            lesson_number=1,
            chunk_index=0
        ),
        CourseChunk(
            content="Machine learning is a subset of AI that focuses on algorithms.",
            course_title="AI Fundamentals", 
            lesson_number=2,
            chunk_index=1
        ),
        CourseChunk(
            content="Deep learning uses neural networks with multiple layers.",
            course_title="AI Fundamentals",
            lesson_number=2,
            chunk_index=2
        )
    ]


@pytest.fixture
def sample_search_results():
    """Create sample search results"""
    return SearchResults(
        documents=[
            "Introduction to artificial intelligence and its applications.",
            "Machine learning is a subset of AI that focuses on algorithms."
        ],
        metadata=[
            {"course_title": "AI Fundamentals", "lesson_number": 1},
            {"course_title": "AI Fundamentals", "lesson_number": 2}
        ],
        distances=[0.1, 0.2]
    )


@pytest.fixture
def empty_search_results():
    """Create empty search results"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )


@pytest.fixture
def error_search_results():
    """Create search results with error"""
    return SearchResults.empty("Test search error")


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = SearchResults(
        documents=["Test content"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.1]
    )
    mock_store.get_lesson_link.return_value = "https://example.com/lesson1"
    mock_store._resolve_course_name.return_value = "Test Course"
    return mock_store


@pytest.fixture
def course_search_tool(mock_vector_store):
    """Create a CourseSearchTool with mocked vector store"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def course_outline_tool(mock_vector_store):
    """Create a CourseOutlineTool with mocked vector store"""
    return CourseOutlineTool(mock_vector_store)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test AI response"
    mock_response.stop_reason = "stop"
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_ai_generator(mock_anthropic_client):
    """Create an AIGenerator with mocked Anthropic client"""
    generator = AIGenerator("fake-api-key", "claude-sonnet-4-20250514")
    generator.client = mock_anthropic_client
    return generator


@pytest.fixture
def mock_tool_manager():
    """Create a mock tool manager"""
    mock_manager = Mock(spec=ToolManager)
    mock_manager.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials"
        }
    ]
    mock_manager.execute_tool.return_value = "Mock tool result"
    mock_manager.get_last_sources.return_value = ["Source 1", "Source 2"]
    return mock_manager


@pytest.fixture
def test_config():
    """Create test configuration"""
    return Config(
        ANTHROPIC_API_KEY="test-key",
        ANTHROPIC_MODEL="claude-sonnet-4-20250514",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=500,
        CHUNK_OVERLAP=50,
        MAX_RESULTS=3,
        MAX_HISTORY=2,
        CHROMA_PATH="./test_chroma_db"
    )


@pytest.fixture
def temp_chroma_path():
    """Create a temporary directory for ChromaDB testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


# Anthropic API response fixtures
@pytest.fixture
def anthropic_tool_use_response():
    """Mock Anthropic response with tool use"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"
    
    # Mock tool use content block
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "search_course_content"
    mock_tool_block.input = {"query": "test query"}
    mock_tool_block.id = "tool_123"
    
    mock_response.content = [mock_tool_block]
    return mock_response


@pytest.fixture
def anthropic_text_response():
    """Mock Anthropic text response"""
    mock_response = Mock()
    mock_response.stop_reason = "stop"
    
    mock_text_block = Mock()
    mock_text_block.text = "This is a test response"
    
    mock_response.content = [mock_text_block]
    return mock_response


@pytest.fixture
def anthropic_sequential_responses():
    """Mock two sequential Anthropic responses for multi-round testing"""
    # First response with tool use
    first_response = Mock()
    first_response.stop_reason = "tool_use"
    
    first_tool_block = Mock()
    first_tool_block.type = "tool_use"
    first_tool_block.name = "search_course_content"
    first_tool_block.input = {"query": "first search"}
    first_tool_block.id = "tool_001"
    
    first_response.content = [first_tool_block]
    
    # Second response with another tool use
    second_response = Mock()
    second_response.stop_reason = "tool_use"
    
    second_tool_block = Mock()
    second_tool_block.type = "tool_use"
    second_tool_block.name = "get_course_outline"
    second_tool_block.input = {"course_name": "test course"}
    second_tool_block.id = "tool_002"
    
    second_response.content = [second_tool_block]
    
    # Final response without tools
    final_response = Mock()
    final_response.stop_reason = "stop"
    
    final_text_block = Mock()
    final_text_block.text = "Final synthesized response after two tool calls"
    
    final_response.content = [final_text_block]
    
    return [first_response, second_response, final_response]


@pytest.fixture
def anthropic_single_round_response():
    """Mock single round response - tool use followed by final text response"""
    # First response with tool use
    tool_response = Mock()
    tool_response.stop_reason = "tool_use"
    
    tool_block = Mock()
    tool_block.type = "tool_use" 
    tool_block.name = "search_course_content"
    tool_block.input = {"query": "single search"}
    tool_block.id = "tool_123"
    
    tool_response.content = [tool_block]
    
    # Final response without tools
    final_response = Mock()
    final_response.stop_reason = "stop"
    
    final_text_block = Mock()
    final_text_block.text = "Response after single tool call"
    
    final_response.content = [final_text_block]
    
    return [tool_response, final_response]


# Utility functions for tests
def create_mock_chroma_results(documents: List[str], metadatas: List[Dict[str, Any]] = None):
    """Helper to create mock ChromaDB results"""
    if metadatas is None:
        metadatas = [{"course_title": f"Course {i}", "lesson_number": i} for i in range(len(documents))]
    
    return {
        'documents': [documents] if documents else [],
        'metadatas': [metadatas] if metadatas else [],
        'distances': [[0.1 * i for i in range(len(documents))]] if documents else []
    }