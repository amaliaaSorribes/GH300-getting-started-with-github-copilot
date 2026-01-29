"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import json
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)

@pytest.fixture
def reset_activities():
    """Reset activities to original state before each test"""
    from app import activities
    # Save original state
    original = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    
    # Clear and reset activities
    activities.clear()
    activities.update(original)
    
    yield activities
    
    # Cleanup after test
    activities.clear()
    activities.update(original)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successfully fetching all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successfully signing up for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]

    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signing up for non-existent activity"""
        response = client.post(
            "/activities/Non-existent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_signup_duplicate_student(self, client, reset_activities):
        """Test signing up when student is already registered"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_new_student_added(self, client, reset_activities):
        """Test that new student is actually added to participants list"""
        client.post(
            "/activities/Chess Club/signup?email=alice@mergington.edu"
        )
        response = client.get("/activities")
        data = response.json()
        assert "alice@mergington.edu" in data["Chess Club"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successfully unregistering from an activity"""
        response = client.request(
            "DELETE",
            "/activities/Chess Club/unregister",
            json={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "michael@mergington.edu" in data["message"]

    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregistering from non-existent activity"""
        response = client.request(
            "DELETE",
            "/activities/Non-existent Club/unregister",
            json={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregistering when student is not registered"""
        response = client.request(
            "DELETE",
            "/activities/Chess Club/unregister",
            json={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_student_removed(self, client, reset_activities):
        """Test that student is actually removed from participants list"""
        client.request(
            "DELETE",
            "/activities/Chess Club/unregister",
            json={"email": "michael@mergington.edu"}
        )
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]


class TestSignupAndUnregisterFlow:
    """Integration tests for signup and unregister flows"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test signing up and then unregistering"""
        # Sign up
        response = client.post(
            "/activities/Chess Club/signup?email=testuser@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert "testuser@mergington.edu" in response.json()["Chess Club"]["participants"]
        
        # Unregister
        response = client.request(
            "DELETE",
            "/activities/Chess Club/unregister",
            json={"email": "testuser@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify unregister
        response = client.get("/activities")
        assert "testuser@mergington.edu" not in response.json()["Chess Club"]["participants"]
    
    def test_multiple_signups(self, client, reset_activities):
        """Test multiple different students signing up"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/Chess Club/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        participants = response.json()["Chess Club"]["participants"]
        for email in emails:
            assert email in participants
