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
from app.core.security import get_password_hash
from app.models.models import User, UserRole, Payment, PaymentStatus, ClaimStatus,Claim,Policy

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

# Import test data from claims test
from tests.test_claims import test_ids, setup_test_data

# Setup additional test data
def setup_payment_test_data():
    db = TestingSessionLocal()
    
    # Create finance user
    finance_user = User(
        email="finance@example.com",
        hashed_password=get_password_hash("finance123"),
        full_name="Finance User",
        role=UserRole.FINANCE,
        is_active=True
    )
    db.add(finance_user)
    db.commit()
    
    # Update claim status to approved
    claim = db.query(Claim).filter(Claim.id == test_ids["claim_id"]).first()
    claim.status = ClaimStatus.APPROVED
    claim.approved_amount = 800.00
    db.commit()
    
    # Create payment
    payment = Payment(
        claim_id=test_ids["claim_id"],
        invoice_number="INV-TEST123",
        payment_amount=800.00,
        payment_date=date(2025, 4, 15),
        payment_status=PaymentStatus.SCHEDULED,
        processed_by_id=finance_user.id
    )
    db.add(payment)
    db.commit()
    
    db.close()
    
    return {
        "finance_user": {"id": finance_user.id, "email": finance_user.email, "password": "finance123"},
        "payment_id": payment.id
    }

# Setup test data
payment_test_ids = setup_payment_test_data()

# Tests for payments
def test_get_payments_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/payments",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one payment

def test_get_payments_finance_user():
    token = get_auth_token(payment_test_ids["finance_user"]["email"], payment_test_ids["finance_user"]["password"])
    response = client.get(
        f"{settings.API_V1_STR}/payments",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one payment

def test_get_payments_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    response = client.get(
        f"{settings.API_V1_STR}/payments",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one payment for this policyholder

def test_get_payment_by_id_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/payments/{payment_test_ids['payment_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(payment_test_ids["payment_id"])
    assert response.json()["invoice_number"] == "INV-TEST123"

def test_get_payment_by_id_finance_user():
    token = get_auth_token(payment_test_ids["finance_user"]["email"], payment_test_ids["finance_user"]["password"])
    response = client.get(
        f"{settings.API_V1_STR}/payments/{payment_test_ids['payment_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(payment_test_ids["payment_id"])
    assert response.json()["invoice_number"] == "INV-TEST123"

def test_get_payment_by_id_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    response = client.get(
        f"{settings.API_V1_STR}/payments/{payment_test_ids['payment_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(payment_test_ids["payment_id"])
    assert response.json()["invoice_number"] == "INV-TEST123"

def test_create_payment_finance_user():
    # First create a new claim for testing
    db = TestingSessionLocal()
    
    # Get policy
    policy = db.query(Policy).filter(Policy.id == test_ids["policy_id"]).first()
    
    # Create new claim
    new_claim = Claim(
        reference_number="CLM-TESTPAY",
        policy_id=policy.id,
        hospital_pharmacy="Test Hospital",
        reason="Medical test for payment",
        requested_amount=1200.00,
        approved_amount=1200.00,
        status=ClaimStatus.APPROVED
    )
    db.add(new_claim)
    db.commit()
    new_claim_id = new_claim.id
    db.close()
    
    # Now create payment for this claim
    token = get_auth_token(payment_test_ids["finance_user"]["email"], payment_test_ids["finance_user"]["password"])
    
    # Create form data
    form_data = {
        "invoice_number": "INV-NEW123",
        "payment_amount": 1200.00,
        "payment_date": "2025-04-20"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/claims/{new_claim_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 200
    assert response.json()["invoice_number"] == "INV-NEW123"
    assert response.json()["payment_amount"] == 1200.00
    assert response.json()["payment_status"] == PaymentStatus.SCHEDULED

def test_update_payment_finance_user():
    token = get_auth_token(payment_test_ids["finance_user"]["email"], payment_test_ids["finance_user"]["password"])
    
    # Update form data
    form_data = {
        "payment_status": PaymentStatus.PROCESSED
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/payments/{payment_test_ids['payment_id']}",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 200
    assert response.json()["payment_status"] == PaymentStatus.PROCESSED

def test_update_payment_policyholder():
    token = get_auth_token(test_policyholder["email"], test_policyholder["password"])
    
    # Update form data
    form_data = {
        "payment_status": PaymentStatus.FAILED
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/payments/{payment_test_ids['payment_id']}",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 403  # Policyholder should not have access

# Run tests
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
