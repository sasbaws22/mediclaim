import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
from datetime import date

from app.db.session import Base, get_db
from app import app
from app.core.config import settings
from app.models.models import User, UserRole, Employer, Policy, Claim, ClaimStatus
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

# Setup test data
def setup_test_data():
    db = TestingSessionLocal()
    
    # Create employer
    employer = Employer(
        name="Test Company",
        contact_person="HR Manager",
        contact_email="hr@testcompany.com",
        contact_phone="1234567890",
        address="123 Test Street, Test City"
    )
    db.add(employer)
    db.commit()
    
    # Get policyholder user
    policyholder = db.query(User).filter(User.email == test_policyholder["email"]).first()
    
    # Create policy
    policy = Policy(
        member_number="MEM12345",
        plan_type="Premium",
        policyholder_id=policyholder.id,
        employer_id=employer.id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        is_active=True
    )
    db.add(policy)
    db.commit()
    
    # Create claim
    claim = Claim(
        reference_number="CLM-TEST123",
        policy_id=policy.id,
        hospital_pharmacy="Test Hospital",
        reason="Medical test",
        requested_amount=1000.00,
        status=ClaimStatus.SUBMITTED
    )
    db.add(claim)
    db.commit()
    
    db.close()
    
    return {
        "employer_id": employer.id,
        "policy_id": policy.id,
        "claim_id": claim.id
    }

# Setup test data
test_ids = setup_test_data()

# Tests for claims
def test_get_claims_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/claims",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one claim

def test_get_claims_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    response = client.get(
        f"{settings.API_V1_STR}/claims",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one claim

def test_get_claim_by_id_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/claims/{test_ids['claim_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(test_ids["claim_id"])
    assert response.json()["reference_number"] == "CLM-TEST123"

def test_get_claim_by_id_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    response = client.get(
        f"{settings.API_V1_STR}/claims/{test_ids['claim_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(test_ids["claim_id"])
    assert response.json()["reference_number"] == "CLM-TEST123"

def test_update_claim_status_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.put(
        f"{settings.API_V1_STR}/claims/{test_ids['claim_id']}/status",
        headers={"Authorization": f"Bearer {token}"},
        data={"status": ClaimStatus.UNDER_REVIEW_CS}
    )
    assert response.status_code == 200
    assert response.json()["status"] == ClaimStatus.UNDER_REVIEW_CS

def test_update_claim_status_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    response = client.put(
        f"{settings.API_V1_STR}/claims/{test_ids['claim_id']}/status",
        headers={"Authorization": f"Bearer {token}"},
        data={"status": ClaimStatus.APPROVED}
    )
    assert response.status_code == 403  # Policyholder should not have access

# Tests for creating a new claim
def test_create_claim_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    
    # Create form data
    form_data = {
        "policy_id": str(test_ids["policy_id"]),
        "hospital_pharmacy": "New Test Hospital",
        "reason": "New medical test",
        "requested_amount": 500.00
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/claims",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 200
    assert "reference_number" in response.json()
    assert response.json()["status"] == ClaimStatus.SUBMITTED

# Run tests
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
