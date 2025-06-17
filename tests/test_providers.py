import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool
from app import app
from app.core.deps import get_db
from app.models.models import Provider

# Create a test database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

def get_test_db():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_db] = get_test_db

client = TestClient(app)

def test_create_provider():
    """Test creating a new provider"""
    provider_data = {
        "name": "Test Insurance Company",
        "contact_person": "John Doe",
        "contact_email": "john.doe@testinsurance.com",
        "contact_phone": "+1234567890"
    }
    
    response = client.post("/v1/providers/", json=provider_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == provider_data["name"]
    assert data["contact_person"] == provider_data["contact_person"]
    assert data["contact_email"] == provider_data["contact_email"]
    assert data["contact_phone"] == provider_data["contact_phone"]
    assert "id" in data

def test_create_provider_duplicate_email():
    """Test creating a provider with duplicate email"""
    provider_data = {
        "name": "Test Insurance Company",
        "contact_person": "John Doe",
        "contact_email": "john.doe@testinsurance.com",
        "contact_phone": "+1234567890"
    }
    
    # Create first provider
    client.post("/v1/providers/", json=provider_data)
    
    # Try to create second provider with same email
    response = client.post("/v1/providers/", json=provider_data)
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_create_provider_missing_fields():
    """Test creating a provider with missing required fields"""
    provider_data = {
        "name": "Test Insurance Company",
        # Missing contact_person, contact_email, contact_phone
    }
    
    response = client.post("/v1/providers/", json=provider_data)
    
    assert response.status_code == 422  # Validation error

