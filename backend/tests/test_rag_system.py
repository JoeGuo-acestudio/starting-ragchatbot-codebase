"""Integration tests for RAG System"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rag_system import RAGSystem
from models import Course
from config import Config
import tempfile
import os


@pytest.mark.integration  
class TestRAGSystem:
    """Test cases for RAG System integration"""

    @pytest.fixture
    def mock_rag_system(self, test_config, mock_tool_manager):
        """Create a RAG system with mocked dependencies"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vector_store, \
             patch('rag_system.AIGenerator') as mock_ai_generator, \
             patch('rag_system.SessionManager') as mock_session_manager, \
             patch('rag_system.ToolManager') as mock_tool_manager_class:
            
            rag = RAGSystem(test_config)
            
            # Configure mocks
            rag.vector_store = mock_vector_store.return_value
            rag.ai_generator = mock_ai_generator.return_value  
            rag.session_manager = mock_session_manager.return_value
            rag.tool_manager = mock_tool_manager
            
            return rag

    def test_init(self, test_config):
        """Test RAG system initialization"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):
            
            rag = RAGSystem(test_config)
            
            assert rag.config == test_config
            assert hasattr(rag, 'document_processor')
            assert hasattr(rag, 'vector_store') 
            assert hasattr(rag, 'ai_generator')
            assert hasattr(rag, 'session_manager')
            assert hasattr(rag, 'tool_manager')
            assert hasattr(rag, 'search_tool')
            assert hasattr(rag, 'outline_tool')

    def test_query_without_session(self, mock_rag_system):
        """Test query processing without session ID"""
        # Mock AI response
        mock_rag_system.ai_generator.generate_response.return_value = "Test response"
        mock_rag_system.tool_manager.get_last_sources.return_value = ["Source 1", "Source 2"]
        
        result, sources = mock_rag_system.query("Test query")
        
        # Verify AI generator was called correctly
        mock_rag_system.ai_generator.generate_response.assert_called_once()
        call_args = mock_rag_system.ai_generator.generate_response.call_args[1]
        
        assert "Answer this question about course materials: Test query" in call_args["query"]
        assert call_args["conversation_history"] is None
        assert call_args["tools"] is not None
        assert call_args["tool_manager"] is not None
        
        # Verify result
        assert result == "Test response"
        assert sources == ["Source 1", "Source 2"]
        
        # Verify sources were reset
        mock_rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_with_session(self, mock_rag_system):
        """Test query processing with session ID"""
        session_id = "test-session-123"
        conversation_history = "Previous conversation"
        
        # Mock session manager
        mock_rag_system.session_manager.get_conversation_history.return_value = conversation_history
        
        # Mock AI response
        mock_rag_system.ai_generator.generate_response.return_value = "Test response"
        mock_rag_system.tool_manager.get_last_sources.return_value = []
        
        result, sources = mock_rag_system.query("Test query", session_id)
        
        # Verify session history was retrieved
        mock_rag_system.session_manager.get_conversation_history.assert_called_once_with(session_id)
        
        # Verify AI generator was called with history
        call_args = mock_rag_system.ai_generator.generate_response.call_args[1]
        assert call_args["conversation_history"] == conversation_history
        
        # Verify session was updated
        mock_rag_system.session_manager.add_exchange.assert_called_once_with(
            session_id, "Test query", "Test response"
        )
        
        assert result == "Test response"

    def test_query_tools_integration(self, mock_rag_system):
        """Test that query properly integrates with tool manager"""
        mock_rag_system.ai_generator.generate_response.return_value = "AI response with tools"
        mock_rag_system.tool_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content", "description": "Search tool"},
            {"name": "get_course_outline", "description": "Outline tool"}
        ]
        mock_rag_system.tool_manager.get_last_sources.return_value = ["Source A", "Source B"]
        
        result, sources = mock_rag_system.query("What is machine learning?")
        
        # Verify tools were provided to AI generator
        call_args = mock_rag_system.ai_generator.generate_response.call_args[1]
        assert len(call_args["tools"]) == 2
        assert call_args["tools"][0]["name"] == "search_course_content"
        assert call_args["tools"][1]["name"] == "get_course_outline"
        
        # Verify tool manager was passed
        assert call_args["tool_manager"] == mock_rag_system.tool_manager
        
        # Verify sources handling
        mock_rag_system.tool_manager.get_last_sources.assert_called_once()
        mock_rag_system.tool_manager.reset_sources.assert_called_once()
        assert sources == ["Source A", "Source B"]

    def test_content_query_workflow(self, mock_rag_system):
        """Test typical content query workflow"""
        # Simulate a content search query
        query = "Explain neural networks in machine learning"
        
        # Mock AI response that would come from using search tool
        ai_response = """Neural networks are computational models inspired by biological neural networks. 

[Machine Learning Course - Lesson 3]
A neural network consists of interconnected nodes (neurons) organized in layers. Each connection has an associated weight that is adjusted during training."""
        
        mock_rag_system.ai_generator.generate_response.return_value = ai_response
        mock_rag_system.tool_manager.get_last_sources.return_value = [
            '<a href="https://example.com/ml-lesson3" target="_blank">Machine Learning Course - Lesson 3</a>'
        ]
        
        result, sources = mock_rag_system.query(query)
        
        # Verify the query was processed correctly
        assert result == ai_response
        assert len(sources) == 1
        assert "Machine Learning Course - Lesson 3" in sources[0]
        assert "https://example.com/ml-lesson3" in sources[0]

    def test_outline_query_workflow(self, mock_rag_system):
        """Test typical course outline query workflow"""
        query = "What is the outline of the Deep Learning course?"
        
        # Mock AI response that would come from outline tool
        ai_response = """**Course:** Deep Learning Fundamentals
**Instructor:** Dr. Johnson
**Course Link:** <a href="https://example.com/deep-learning" target="_blank">https://example.com/deep-learning</a>
**Total Lessons:** 8

**Lesson Structure:**
1. <a href="https://example.com/lesson1" target="_blank">Introduction to Deep Learning</a>
2. <a href="https://example.com/lesson2" target="_blank">Neural Network Basics</a>"""
        
        mock_rag_system.ai_generator.generate_response.return_value = ai_response
        mock_rag_system.tool_manager.get_last_sources.return_value = []  # Outline tool doesn't use sources
        
        result, sources = mock_rag_system.query(query)
        
        # Verify the outline query was processed
        assert result == ai_response
        assert "Course:" in result
        assert "Course Link:" in result 
        assert "Lesson Structure:" in result
        assert sources == []

    def test_add_course_document(self, mock_rag_system, sample_course, sample_course_chunks):
        """Test adding a single course document"""
        file_path = "/test/course.txt"
        
        # Mock document processor
        mock_rag_system.document_processor.process_course_document.return_value = (
            sample_course, sample_course_chunks
        )
        
        course, chunk_count = mock_rag_system.add_course_document(file_path)
        
        # Verify document processor was called
        mock_rag_system.document_processor.process_course_document.assert_called_once_with(file_path)
        
        # Verify vector store operations
        mock_rag_system.vector_store.add_course_metadata.assert_called_once_with(sample_course)
        mock_rag_system.vector_store.add_course_content.assert_called_once_with(sample_course_chunks)
        
        # Verify return values
        assert course == sample_course
        assert chunk_count == len(sample_course_chunks)

    def test_add_course_document_error(self, mock_rag_system):
        """Test error handling in add_course_document"""
        file_path = "/test/invalid.txt"
        
        # Mock document processor error
        mock_rag_system.document_processor.process_course_document.side_effect = Exception("Processing error")
        
        with patch('builtins.print') as mock_print:
            course, chunk_count = mock_rag_system.add_course_document(file_path)
        
        # Verify error handling
        assert course is None
        assert chunk_count == 0
        mock_print.assert_called_with("Error processing course document /test/invalid.txt: Processing error")

    def test_add_course_folder_new_courses(self, mock_rag_system, sample_course, sample_course_chunks):
        """Test adding courses from folder with new courses"""
        folder_path = "/test/courses/"
        
        # Mock existing courses (empty)
        mock_rag_system.vector_store.get_existing_course_titles.return_value = []
        
        # Create different courses to avoid duplicate detection
        course1 = sample_course
        course2 = Course(
            title="Different Course",
            course_link="https://example.com/course2",
            instructor="Dr. Johnson",
            lessons=sample_course.lessons
        )
        
        # Mock document processor to return different courses
        mock_rag_system.document_processor.process_course_document.side_effect = [
            (course1, sample_course_chunks),
            (course2, sample_course_chunks)
        ]
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['course1.txt', 'course2.pdf']), \
             patch('os.path.isfile', return_value=True), \
             patch('builtins.print') as mock_print:
            
            total_courses, total_chunks = mock_rag_system.add_course_folder(folder_path)
        
        # Verify processing 
        assert mock_rag_system.document_processor.process_course_document.call_count == 2
        assert mock_rag_system.vector_store.add_course_metadata.call_count == 2
        assert mock_rag_system.vector_store.add_course_content.call_count == 2
        
        # Verify results
        assert total_courses == 2
        assert total_chunks == len(sample_course_chunks) * 2
        
        # Verify logging for both courses
        mock_print.assert_any_call(f"Added new course: {course1.title} ({len(sample_course_chunks)} chunks)")
        mock_print.assert_any_call(f"Added new course: {course2.title} ({len(sample_course_chunks)} chunks)")

    def test_add_course_folder_existing_courses(self, mock_rag_system, sample_course, sample_course_chunks):
        """Test adding courses from folder with existing courses"""
        folder_path = "/test/courses/"
        
        # Mock existing courses
        mock_rag_system.vector_store.get_existing_course_titles.return_value = [sample_course.title]
        
        # Mock document processor
        mock_rag_system.document_processor.process_course_document.return_value = (
            sample_course, sample_course_chunks
        )
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['course1.txt']), \
             patch('os.path.isfile', return_value=True), \
             patch('builtins.print') as mock_print:
            
            total_courses, total_chunks = mock_rag_system.add_course_folder(folder_path)
        
        # Verify course was skipped
        assert total_courses == 0
        assert total_chunks == 0
        mock_print.assert_any_call(f"Course already exists: {sample_course.title} - skipping")

    def test_add_course_folder_clear_existing(self, mock_rag_system):
        """Test adding courses with clear_existing=True"""
        folder_path = "/test/courses/"
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=[]), \
             patch('builtins.print') as mock_print:
            
            mock_rag_system.add_course_folder(folder_path, clear_existing=True)
        
        # Verify data was cleared
        mock_rag_system.vector_store.clear_all_data.assert_called_once()
        mock_print.assert_any_call("Clearing existing data for fresh rebuild...")

    def test_add_course_folder_nonexistent(self, mock_rag_system):
        """Test adding courses from non-existent folder"""
        folder_path = "/nonexistent/courses/"
        
        with patch('os.path.exists', return_value=False), \
             patch('builtins.print') as mock_print:
            
            total_courses, total_chunks = mock_rag_system.add_course_folder(folder_path)
        
        assert total_courses == 0
        assert total_chunks == 0
        mock_print.assert_called_with(f"Folder {folder_path} does not exist")

    def test_get_course_analytics(self, mock_rag_system):
        """Test getting course analytics"""
        # Mock vector store methods
        mock_rag_system.vector_store.get_course_count.return_value = 5
        mock_rag_system.vector_store.get_existing_course_titles.return_value = [
            "Course A", "Course B", "Course C", "Course D", "Course E"
        ]
        
        analytics = mock_rag_system.get_course_analytics()
        
        # Verify analytics structure
        assert analytics["total_courses"] == 5
        assert len(analytics["course_titles"]) == 5
        assert "Course A" in analytics["course_titles"]

    def test_session_workflow(self, mock_rag_system):
        """Test complete session workflow with multiple queries"""
        session_id = "session-123"
        
        # Mock session manager behavior
        mock_rag_system.session_manager.get_conversation_history.side_effect = [
            None,  # First query - no history
            "Q: What is AI? A: Artificial Intelligence...",  # Second query - has history
        ]
        
        mock_rag_system.ai_generator.generate_response.side_effect = [
            "AI is artificial intelligence.",
            "Machine learning is a subset of AI."
        ]
        
        mock_rag_system.tool_manager.get_last_sources.return_value = []
        
        # First query
        result1, sources1 = mock_rag_system.query("What is AI?", session_id)
        
        # Second query
        result2, sources2 = mock_rag_system.query("What about machine learning?", session_id)
        
        # Verify session updates
        assert mock_rag_system.session_manager.add_exchange.call_count == 2
        mock_rag_system.session_manager.add_exchange.assert_any_call(
            session_id, "What is AI?", "AI is artificial intelligence."
        )
        mock_rag_system.session_manager.add_exchange.assert_any_call(
            session_id, "What about machine learning?", "Machine learning is a subset of AI."
        )
        
        # Verify conversation history was used in second query
        second_call_args = mock_rag_system.ai_generator.generate_response.call_args_list[1][1]
        assert second_call_args["conversation_history"] == "Q: What is AI? A: Artificial Intelligence..."