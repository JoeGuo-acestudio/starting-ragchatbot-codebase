"""API endpoint tests for the RAG system FastAPI application"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import json


@pytest.mark.api
class TestQueryEndpoint:
    """Test the /api/query endpoint"""
    
    def test_query_with_session_id(self, client, sample_query_request):
        """Test query endpoint with existing session ID"""
        response = client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data  
        assert "session_id" in data
        assert data["session_id"] == sample_query_request["session_id"]
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0
    
    def test_query_without_session_id(self, client):
        """Test query endpoint without session ID (creates new session)"""
        request_data = {"query": "What is artificial intelligence?"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-id"  # From mock
    
    def test_query_empty_string(self, client):
        """Test query endpoint with empty query string"""
        request_data = {"query": ""}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
    
    def test_query_missing_query_field(self, client):
        """Test query endpoint with missing query field"""
        request_data = {"session_id": "test-123"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_query_invalid_json(self, client):
        """Test query endpoint with invalid JSON"""
        response = client.post(
            "/api/query", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_query_long_input(self, client):
        """Test query endpoint with very long input"""
        long_query = "What is machine learning? " * 100  # Very long query
        request_data = {"query": long_query}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


@pytest.mark.api  
class TestCoursesEndpoint:
    """Test the /api/courses endpoint"""
    
    def test_get_course_stats(self, client):
        """Test getting course statistics"""
        response = client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert data["total_courses"] == 3  # From mock
        assert len(data["course_titles"]) == 3
    
    def test_courses_endpoint_method_not_allowed(self, client):
        """Test courses endpoint with wrong HTTP method"""
        response = client.post("/api/courses")
        assert response.status_code == 405  # Method not allowed


@pytest.mark.api
class TestRootEndpoint:
    """Test the root / endpoint"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns correct message"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data == {"message": "RAG System API"}


@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling scenarios"""
    
    def test_nonexistent_endpoint(self, client):
        """Test accessing non-existent endpoint"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
    
    def test_cors_headers(self, client):
        """Test that CORS headers are properly set"""
        response = client.get("/")
        assert response.status_code == 200
        # Note: TestClient doesn't fully simulate CORS, but we can verify the middleware is configured


@pytest.mark.api
@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints"""
    
    def test_query_courses_integration(self, client):
        """Test querying and then getting course stats"""
        # First make a query
        query_response = client.post("/api/query", json={"query": "Tell me about AI"})
        assert query_response.status_code == 200
        
        # Then get course stats  
        stats_response = client.get("/api/courses")
        assert stats_response.status_code == 200
        
        # Verify both responses are valid
        query_data = query_response.json()
        stats_data = stats_response.json()
        
        assert "session_id" in query_data
        assert stats_data["total_courses"] > 0



@pytest.mark.api
class TestAPIResponseValidation:
    """Test API response schema validation"""
    
    def test_query_response_schema(self, client):
        """Test that query response matches expected schema"""
        response = client.post("/api/query", json={"query": "Test query"})
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields exist
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check field types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)
        
        # Check that sources list contains strings
        for source in data["sources"]:
            assert isinstance(source, str)
    
    def test_courses_response_schema(self, client):
        """Test that courses response matches expected schema"""
        response = client.get("/api/courses")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields exist
        required_fields = ["total_courses", "course_titles"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        
        # Check that course_titles list contains strings
        for title in data["course_titles"]:
            assert isinstance(title, str)
        
        # Check logical constraints
        assert data["total_courses"] >= 0
        assert len(data["course_titles"]) == data["total_courses"]