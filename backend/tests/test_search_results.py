"""Unit tests for SearchResults"""

import pytest
from vector_store import SearchResults


@pytest.mark.unit
class TestSearchResults:
    """Test cases for SearchResults dataclass"""

    def test_init_basic(self):
        """Test basic SearchResults initialization"""
        results = SearchResults(
            documents=["doc1", "doc2"],
            metadata=[{"key": "value1"}, {"key": "value2"}],
            distances=[0.1, 0.2]
        )
        
        assert results.documents == ["doc1", "doc2"]
        assert results.metadata == [{"key": "value1"}, {"key": "value2"}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None

    def test_init_with_error(self):
        """Test SearchResults initialization with error"""
        results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Search failed"
        )
        
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error == "Search failed"

    def test_from_chroma_with_data(self):
        """Test creating SearchResults from ChromaDB results with data"""
        chroma_results = {
            'documents': [["doc1", "doc2", "doc3"]],
            'metadatas': [[{"course": "A"}, {"course": "B"}, {"course": "C"}]],
            'distances': [[0.1, 0.2, 0.3]]
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        assert results.documents == ["doc1", "doc2", "doc3"]
        assert results.metadata == [{"course": "A"}, {"course": "B"}, {"course": "C"}]
        assert results.distances == [0.1, 0.2, 0.3]
        assert results.error is None

    def test_from_chroma_with_empty_data(self):
        """Test creating SearchResults from empty ChromaDB results"""
        chroma_results = {
            'documents': [],
            'metadatas': [],
            'distances': []
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error is None

    def test_from_chroma_with_none_data(self):
        """Test creating SearchResults from ChromaDB results with None values"""
        chroma_results = {
            'documents': None,
            'metadatas': None,
            'distances': None
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error is None

    def test_from_chroma_partial_data(self):
        """Test creating SearchResults from ChromaDB with some missing fields"""
        chroma_results = {
            'documents': [["doc1"]],
            'metadatas': None,
            'distances': [[0.1]]
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        assert results.documents == ["doc1"]
        assert results.metadata == []
        assert results.distances == [0.1]

    def test_empty_classmethod(self):
        """Test creating empty SearchResults with error message"""
        error_msg = "No results found"
        results = SearchResults.empty(error_msg)
        
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error == error_msg

    def test_is_empty_true(self):
        """Test is_empty returns True for empty results"""
        results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        
        assert results.is_empty() is True

    def test_is_empty_false(self):
        """Test is_empty returns False for non-empty results"""
        results = SearchResults(
            documents=["doc1"],
            metadata=[{"key": "value"}],
            distances=[0.1]
        )
        
        assert results.is_empty() is False

    def test_is_empty_with_error(self):
        """Test is_empty behavior with error message"""
        # Empty results with error should still be considered empty
        results = SearchResults.empty("Error occurred")
        
        assert results.is_empty() is True
        assert results.error == "Error occurred"

    def test_equality(self):
        """Test SearchResults equality comparison"""
        results1 = SearchResults(
            documents=["doc1"],
            metadata=[{"key": "value"}],
            distances=[0.1]
        )
        
        results2 = SearchResults(
            documents=["doc1"],
            metadata=[{"key": "value"}],
            distances=[0.1]
        )
        
        # Note: dataclasses automatically provide __eq__ method
        assert results1 == results2

    def test_inequality(self):
        """Test SearchResults inequality comparison"""
        results1 = SearchResults(
            documents=["doc1"],
            metadata=[{"key": "value"}],
            distances=[0.1]
        )
        
        results2 = SearchResults(
            documents=["doc2"],
            metadata=[{"key": "value"}],
            distances=[0.1]
        )
        
        assert results1 != results2

    def test_realistic_course_data(self):
        """Test SearchResults with realistic course data"""
        results = SearchResults(
            documents=[
                "Introduction to machine learning algorithms",
                "Deep learning and neural networks"
            ],
            metadata=[
                {
                    "course_title": "ML Fundamentals",
                    "lesson_number": 1,
                    "chunk_index": 0
                },
                {
                    "course_title": "Deep Learning",
                    "lesson_number": 3,
                    "chunk_index": 5
                }
            ],
            distances=[0.12, 0.34]
        )
        
        assert len(results.documents) == 2
        assert len(results.metadata) == 2
        assert len(results.distances) == 2
        
        # Check first result
        assert "machine learning" in results.documents[0]
        assert results.metadata[0]["course_title"] == "ML Fundamentals"
        assert results.metadata[0]["lesson_number"] == 1
        
        # Check second result
        assert "neural networks" in results.documents[1]
        assert results.metadata[1]["course_title"] == "Deep Learning"
        assert results.metadata[1]["lesson_number"] == 3

    def test_mismatched_lengths(self):
        """Test SearchResults with mismatched array lengths"""
        # This tests the flexibility of the dataclass - it doesn't enforce length matching
        results = SearchResults(
            documents=["doc1", "doc2"],
            metadata=[{"key": "value"}],  # Only one metadata item
            distances=[0.1, 0.2, 0.3]  # Three distances
        )
        
        # Should still work - validation is handled at usage level
        assert len(results.documents) == 2
        assert len(results.metadata) == 1
        assert len(results.distances) == 3

    def test_chroma_results_edge_cases(self):
        """Test from_chroma with various edge cases"""
        # Test with nested empty lists
        chroma_results = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }
        
        results = SearchResults.from_chroma(chroma_results)
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []

    def test_chroma_results_missing_keys(self):
        """Test from_chroma with missing dictionary keys"""
        # Missing 'documents' key
        chroma_results = {
            'metadatas': [[{"course": "test"}]],
            'distances': [[0.1]]
        }
        
        # This should raise KeyError in the actual implementation
        with pytest.raises(KeyError):
            SearchResults.from_chroma(chroma_results)

    def test_string_representation(self):
        """Test string representation of SearchResults"""
        results = SearchResults(
            documents=["doc1"],
            metadata=[{"course": "test"}],
            distances=[0.1],
            error=None
        )
        
        # Test that it has a reasonable string representation
        str_repr = str(results)
        assert "SearchResults" in str_repr
        assert "doc1" in str_repr

    def test_error_propagation(self):
        """Test that error messages are properly stored and accessible"""
        error_message = "Vector store connection failed"
        results = SearchResults.empty(error_message)
        
        assert results.error == error_message
        assert results.is_empty()
        
        # Verify error persists
        assert results.error is not None
        assert len(results.error) > 0

    def test_complex_metadata_structure(self):
        """Test SearchResults with complex metadata structures"""
        complex_metadata = [
            {
                "course_title": "Advanced ML",
                "lesson_number": 5,
                "chunk_index": 12,
                "tags": ["supervised", "classification"],
                "difficulty": "advanced",
                "estimated_time": 45
            },
            {
                "course_title": "Basic Stats",
                "lesson_number": 2,
                "chunk_index": 3,
                "tags": ["statistics", "probability"],
                "difficulty": "beginner",
                "estimated_time": 20
            }
        ]
        
        results = SearchResults(
            documents=["Advanced ML content", "Basic stats content"],
            metadata=complex_metadata,
            distances=[0.05, 0.15]
        )
        
        # Verify complex metadata is preserved
        assert results.metadata[0]["tags"] == ["supervised", "classification"]
        assert results.metadata[1]["difficulty"] == "beginner"
        assert results.metadata[0]["estimated_time"] == 45

    def test_dataclass_fields(self):
        """Test that SearchResults has expected dataclass fields"""
        from dataclasses import fields
        
        result_fields = [f.name for f in fields(SearchResults)]
        expected_fields = ["documents", "metadata", "distances", "error"]
        
        assert set(result_fields) == set(expected_fields)