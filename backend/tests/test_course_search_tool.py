"""Unit tests for CourseSearchTool"""

from unittest.mock import Mock, patch

import pytest
from search_tools import CourseSearchTool
from vector_store import SearchResults


@pytest.mark.unit
class TestCourseSearchTool:
    """Test cases for CourseSearchTool"""

    def test_get_tool_definition(self, course_search_tool):
        """Test that tool definition is correctly structured"""
        definition = course_search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition

        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]
        assert schema["required"] == ["query"]

    def test_execute_with_query_only(
        self, course_search_tool, mock_vector_store, sample_search_results
    ):
        """Test execute with only query parameter"""
        mock_vector_store.search.return_value = sample_search_results

        result = course_search_tool.execute("test query")

        # Verify vector store was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name=None, lesson_number=None
        )

        # Verify result format
        assert "[AI Fundamentals - Lesson 1]" in result
        assert "Introduction to artificial intelligence" in result
        assert "[AI Fundamentals - Lesson 2]" in result
        assert "Machine learning is a subset" in result

    def test_execute_with_course_name_filter(
        self, course_search_tool, mock_vector_store, sample_search_results
    ):
        """Test execute with course name filter"""
        mock_vector_store.search.return_value = sample_search_results

        result = course_search_tool.execute("test query", course_name="AI Fundamentals")

        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name="AI Fundamentals", lesson_number=None
        )

        assert result is not None
        assert len(result) > 0

    def test_execute_with_lesson_number_filter(
        self, course_search_tool, mock_vector_store, sample_search_results
    ):
        """Test execute with lesson number filter"""
        mock_vector_store.search.return_value = sample_search_results

        result = course_search_tool.execute("test query", lesson_number=1)

        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name=None, lesson_number=1
        )

        assert result is not None

    def test_execute_with_both_filters(
        self, course_search_tool, mock_vector_store, sample_search_results
    ):
        """Test execute with both course name and lesson number filters"""
        mock_vector_store.search.return_value = sample_search_results

        result = course_search_tool.execute(
            "test query", course_name="AI Fundamentals", lesson_number=2
        )

        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name="AI Fundamentals", lesson_number=2
        )

        assert result is not None

    def test_execute_with_search_error(
        self, course_search_tool, mock_vector_store, error_search_results
    ):
        """Test execute when search returns an error"""
        mock_vector_store.search.return_value = error_search_results

        result = course_search_tool.execute("test query")

        assert result == "Test search error"

    def test_execute_with_empty_results(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute when search returns no results"""
        mock_vector_store.search.return_value = empty_search_results

        result = course_search_tool.execute("test query")

        assert result == "No relevant content found."

    def test_execute_with_empty_results_and_course_filter(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute with empty results and course name filter"""
        mock_vector_store.search.return_value = empty_search_results

        result = course_search_tool.execute("test query", course_name="AI Fundamentals")

        assert result == "No relevant content found in course 'AI Fundamentals'."

    def test_execute_with_empty_results_and_lesson_filter(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute with empty results and lesson number filter"""
        mock_vector_store.search.return_value = empty_search_results

        result = course_search_tool.execute("test query", lesson_number=1)

        assert result == "No relevant content found in lesson 1."

    def test_execute_with_empty_results_and_both_filters(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute with empty results and both filters"""
        mock_vector_store.search.return_value = empty_search_results

        result = course_search_tool.execute(
            "test query", course_name="AI Fundamentals", lesson_number=1
        )

        assert (
            result
            == "No relevant content found in course 'AI Fundamentals' in lesson 1."
        )

    def test_format_results_with_lesson_links(
        self, course_search_tool, mock_vector_store
    ):
        """Test _format_results method with lesson links"""
        # Setup search results
        search_results = SearchResults(
            documents=["Test content 1", "Test content 2"],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1},
                {"course_title": "Test Course", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )

        # Mock lesson links
        mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/lesson1",
            "https://example.com/lesson2",
        ]

        result = course_search_tool._format_results(search_results)

        # Verify format
        assert "[Test Course - Lesson 1]" in result
        assert "Test content 1" in result
        assert "[Test Course - Lesson 2]" in result
        assert "Test content 2" in result

        # Verify sources were generated with links
        assert len(course_search_tool.last_sources) == 2
        assert (
            '<a href="https://example.com/lesson1"'
            in course_search_tool.last_sources[0]
        )
        assert (
            '<a href="https://example.com/lesson2"'
            in course_search_tool.last_sources[1]
        )

    def test_format_results_without_lesson_links(
        self, course_search_tool, mock_vector_store
    ):
        """Test _format_results method without lesson links"""
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
        )

        # Mock no lesson link available
        mock_vector_store.get_lesson_link.return_value = None

        result = course_search_tool._format_results(search_results)

        # Verify plain text source
        assert len(course_search_tool.last_sources) == 1
        assert course_search_tool.last_sources[0] == "Test Course - Lesson 1"

    def test_format_results_without_lesson_number(
        self, course_search_tool, mock_vector_store
    ):
        """Test _format_results method without lesson number in metadata"""
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course"}],  # No lesson_number
            distances=[0.1],
        )

        result = course_search_tool._format_results(search_results)

        # Verify format without lesson number
        assert "[Test Course]" in result
        assert "Test content" in result

        # Verify source without lesson number
        assert len(course_search_tool.last_sources) == 1
        assert course_search_tool.last_sources[0] == "Test Course"

    def test_format_results_with_unknown_course(
        self, course_search_tool, mock_vector_store
    ):
        """Test _format_results method with missing course title"""
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{}],  # No course_title
            distances=[0.1],
        )

        result = course_search_tool._format_results(search_results)

        # Verify unknown course handling
        assert "[unknown]" in result

    def test_last_sources_tracking(
        self, course_search_tool, mock_vector_store, sample_search_results
    ):
        """Test that last_sources is properly tracked"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/lesson1",
            "https://example.com/lesson2",
        ]

        # Initially empty
        assert course_search_tool.last_sources == []

        # Execute search
        course_search_tool.execute("test query")

        # Verify sources were tracked
        assert len(course_search_tool.last_sources) == 2
        assert "AI Fundamentals - Lesson 1" in course_search_tool.last_sources[0]
        assert "AI Fundamentals - Lesson 2" in course_search_tool.last_sources[1]

    def test_sources_reset_on_new_search(self, course_search_tool, mock_vector_store):
        """Test that sources are reset on new search"""
        # Setup first search
        search_results1 = SearchResults(
            documents=["Content 1"],
            metadata=[{"course_title": "Course 1", "lesson_number": 1}],
            distances=[0.1],
        )
        mock_vector_store.search.return_value = search_results1
        course_search_tool.execute("query 1")

        initial_sources = course_search_tool.last_sources.copy()
        assert len(initial_sources) == 1

        # Setup second search
        search_results2 = SearchResults(
            documents=["Content 2", "Content 3"],
            metadata=[
                {"course_title": "Course 2", "lesson_number": 1},
                {"course_title": "Course 2", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )
        mock_vector_store.search.return_value = search_results2
        course_search_tool.execute("query 2")

        # Verify sources were replaced, not appended
        assert len(course_search_tool.last_sources) == 2
        assert course_search_tool.last_sources != initial_sources
