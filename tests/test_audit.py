import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
from datetime import datetime

from app.db.session import Base, get_db
from app import app
from app.core.config import settings
from app.models.models import User, UserRole, AuditLog, AuditAction
from app.core.security import get_password_hash

# Import test setup from auth_users test
from tests.test_auth_users import (
    SQLALCHEMY_DATABASE_URL,
    engine,
    TestingSessionLocal,
    override_get_db,
    client,
    get_auth_token,
    test_admin,
    test_policyholder
)

# Tests for audit trail
def test_login_creates_audit_log():
    # Clear existing audit logs
    db = TestingSessionLocal()
    db.query(AuditLog).delete()
    db.commit()
    
    # Login to create an audit log
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": test_admin["email"], "password": test_admin["password"]}
    )
    assert response.status_code == 200
    
    # Check if audit log was created
    audit_logs = db.query(AuditLog).all()
    assert len(audit_logs) >= 1
    
    # Find the login audit log
    login_log = None
    for log in audit_logs:
        if log.action == AuditAction.LOGIN:
            login_log = log
            break
    
    assert login_log is not None
    assert login_log.entity_type == "User"
    
    # Get the admin user
    admin_user = db.query(User).filter(User.email == test_admin["email"]).first()
    assert login_log.user_id == admin_user.id
    
    db.close()

def test_get_audit_logs_admin():
    # Login as admin
    token = get_auth_token(test_admin["email"], test_admin["password"])
    
    # Get audit logs
    response = client.get(
        f"{settings.API_V1_STR}/audit",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one audit log

def test_get_audit_logs_policyholder():
    # Login as policyholder
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    
    # Get audit logs (should be forbidden for non-admin)
    response = client.get(
        f"{settings.API_V1_STR}/audit",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403  # Forbidden

def test_get_audit_summary():
    # Login as admin
    token = get_auth_token(test_admin["email"], test_admin["password"])
    
    # Get audit summary
    response = client.get(
        f"{settings.API_V1_STR}/audit/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "total_count" in response.json()
    assert "action_counts" in response.json()
    assert "entity_counts" in response.json()
    assert "user_counts" in response.json()

def test_get_audit_log_by_id():
    # Login as admin
    token = get_auth_token(test_admin["email"], test_admin["password"])
    
    # Get all audit logs
    response = client.get(
        f"{settings.API_V1_STR}/audit",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    audit_logs = response.json()
    
    if len(audit_logs) > 0:
        # Get a specific audit log
        log_id = audit_logs[0]["id"]
        response = client.get(
            f"{settings.API_V1_STR}/audit/{log_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == log_id

def test_filter_audit_logs():
    # Login as admin
    token = get_auth_token(test_admin["email"], test_admin["password"])
    
    # Get audit logs filtered by action
    response = client.get(
        f"{settings.API_V1_STR}/audit?action_type={AuditAction.LOGIN}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    logs = response.json()
    
    # All returned logs should have the LOGIN action
    for log in logs:
        assert log["action"] == AuditAction.LOGIN

def test_register_creates_audit_log():
    # Clear existing audit logs
    db = TestingSessionLocal()
    db.query(AuditLog).delete()
    db.commit()
    
    # Register a new user
    new_user = {
        "email": f"newuser_{uuid.uuid4()}@example.com",
        "password": "newuser123",
        "full_name": "New Test User"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=new_user
    )
    assert response.status_code == 200
    
    # Check if audit log was created
    audit_logs = db.query(AuditLog).all()
    assert len(audit_logs) >= 1
    
    # Find the create audit log
    create_log = None
    for log in audit_logs:
        if log.action == AuditAction.CREATE and log.entity_type == "User":
            create_log = log
            break
    
    assert create_log is not None
    assert "email" in create_log.details
    assert create_log.details["email"] == new_user["email"]
    
    db.close()

# Run tests
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
