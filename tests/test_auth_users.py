import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app import app
from app.core.config import settings
from app.models.models import User, UserRole
from app.core.security import get_password_hash

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Setup test database
Base.metadata.create_all(bind=engine)

# Override get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test client
client = TestClient(app)

# Test data
test_admin = {
    "email": "admin@example.com",
    "password": "admin123",
    "full_name": "Admin User",
    "role": UserRole.ADMIN
}

test_policyholder = {
    "email": "user@example.com",
    "password": "user123",
    "full_name": "Test User",
    "role": UserRole.POLICYHOLDER
}

# Setup test data
def setup_test_data():
    db = TestingSessionLocal()
    
    # Create admin user
    admin_user = User(
        email=test_admin["email"],
        hashed_password=get_password_hash(test_admin["password"]),
        full_name=test_admin["full_name"],
        role=test_admin["role"],
        is_active=True
    )
    db.add(admin_user)
    
    # Create policyholder user
    policyholder_user = User(
        email=test_policyholder["email"],
        hashed_password=get_password_hash(test_policyholder["password"]),
        full_name=test_policyholder["full_name"],
        role=test_policyholder["role"],
        is_active=True
    )
    db.add(policyholder_user)
    
    db.commit()
    db.close()

# Helper function to get auth token
def get_auth_token(email, password):
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": email, "password": password}
    )
    return response.json()["access_token"]

# Setup test data before running tests
setup_test_data()

# Tests
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_login_admin():
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": test_admin["email"], "password": test_admin["password"]}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_policyholder():
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": test_policyholder["email"], "password": test_policyholder["password"]}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials():
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "invalid@example.com", "password": "invalid"}
    )
    assert response.status_code == 401

def test_get_current_user():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == test_admin["email"]
    assert response.json()["full_name"] == test_admin["full_name"]
    assert response.json()["role"] == test_admin["role"]

def test_get_users_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2  # At least admin and policyholder users

def test_get_users_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    response = client.get(
        f"{settings.API_V1_STR}/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403  # Policyholder should not have access

def test_create_user_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    new_user = {
        "email": "newuser@example.com",
        "password": "newuser123",
        "full_name": "New User",
        "role": UserRole.HR
    }
    response = client.post(
        f"{settings.API_V1_STR}/users",
        headers={"Authorization": f"Bearer {token}"},
        json=new_user
    )
    assert response.status_code == 200
    assert response.json()["email"] == new_user["email"]
    assert response.json()["full_name"] == new_user["full_name"]
    assert response.json()["role"] == new_user["role"]

def test_create_user_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    new_user = {
        "email": "newuser2@example.com",
        "password": "newuser123",
        "full_name": "New User 2",
        "role": UserRole.HR
    }
    response = client.post(
        f"{settings.API_V1_STR}/users",
        headers={"Authorization": f"Bearer {token}"},
        json=new_user
    )
    assert response.status_code == 403  # Policyholder should not have access

def test_register_user():
    new_user = {
        "email": "newpolicyholder@example.com",
        "password": "newuser123",
        "full_name": "New Policyholder",
        "role": "ADMIN"  # This should be ignored and set to POLICYHOLDER
    }
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=new_user
    )
    assert response.status_code == 200
    assert response.json()["email"] == new_user["email"]
    assert response.json()["full_name"] == new_user["full_name"]
    assert response.json()["role"] == UserRole.POLICYHOLDER  # Role should be POLICYHOLDER regardless of input

def test_update_user_me():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    update_data = {
        "full_name": "Updated User Name"
    }
    response = client.put(
        f"{settings.API_V1_STR}/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == update_data["full_name"]
    assert response.json()["email"] == test_policyholder["email"]  # Email should not change

# Run tests
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
