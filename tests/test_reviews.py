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
from app.models.models import User, UserRole, Review, ReviewType, ReviewDecision, ReviewItem, ReviewItemStatus

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
def setup_review_test_data():
    db = TestingSessionLocal()
    
    # Create CS user
    cs_user = User(
        email="cs@example.com",
        hashed_password=get_password_hash("cs123"),
        full_name="CS User",
        role=UserRole.CUSTOMER_SERVICE,
        is_active=True
    )
    db.add(cs_user)
    
    # Create Claims user
    claims_user = User(
        email="claims@example.com",
        hashed_password=get_password_hash("claims123"),
        full_name="Claims User",
        role=UserRole.CLAIMS,
        is_active=True
    )
    db.add(claims_user)
    
    # Create MD user
    md_user = User(
        email="md@example.com",
        hashed_password=get_password_hash("md123"),
        full_name="MD User",
        role=UserRole.MD,
        is_active=True
    )
    db.add(md_user)
    
    db.commit()
    
    # Create review
    review = Review(
        claim_id=test_ids["claim_id"],
        reviewer_id=cs_user.id,
        review_type=ReviewType.CUSTOMER_SERVICE,
        comments="Initial review",
        decision=ReviewDecision.APPROVED,
    )
    db.add(review)
    db.commit()
    
    # Create review item
    review_item = ReviewItem(
        review_id=review.id,
        item_name="Consultation",
        requested_amount=500.00,
        approved_amount=500.00,
        status=ReviewItemStatus.APPROVED
    )
    db.add(review_item)
    db.commit()
    
    db.close()
    
    return {
        "cs_user": {"id": cs_user.id, "email": cs_user.email, "password": "cs123"},
        "claims_user": {"id": claims_user.id, "email": claims_user.email, "password": "claims123"},
        "md_user": {"id": md_user.id, "email": md_user.email, "password": "md123"},
        "review_id": review.id,
        "review_item_id": review_item.id
    }

# Setup test data
review_test_ids = setup_review_test_data()

# Tests for reviews
def test_get_reviews_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/reviews",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one review

def test_get_reviews_cs_user():
    token = get_auth_token(review_test_ids["cs_user"]["email"], review_test_ids["cs_user"]["password"])
    response = client.get(
        f"{settings.API_V1_STR}/reviews",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1  # At least one review

def test_get_review_by_id_admin():
    token = get_auth_token(test_admin["email"], test_admin["password"])
    response = client.get(
        f"{settings.API_V1_STR}/reviews/{review_test_ids['review_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(review_test_ids["review_id"])
    assert response.json()["review_type"] == ReviewType.CUSTOMER_SERVICE

def test_get_review_by_id_cs_user():
    token = get_auth_token(review_test_ids["cs_user"]["email"], review_test_ids["cs_user"]["password"])
    response = client.get(
        f"{settings.API_V1_STR}/reviews/{review_test_ids['review_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(review_test_ids["review_id"])
    assert response.json()["review_type"] == ReviewType.CUSTOMER_SERVICE

def test_create_review_claims_user():
    token = get_auth_token(review_test_ids["claims_user"]["email"], review_test_ids["claims_user"]["password"])
    
    # Create form data
    form_data = {
        "review_type": ReviewType.CLAIMS,
        "comments": "Claims department review",
        "decision": ReviewDecision.APPROVED,
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/claims/{test_ids['claim_id']}/reviews",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 200
    assert response.json()["review_type"] == ReviewType.CLAIMS
    assert response.json()["decision"] == ReviewDecision.APPROVED

def test_update_review_cs_user():
    token = get_auth_token(review_test_ids["cs_user"]["email"], review_test_ids["cs_user"]["password"])
    
    # Update form data
    form_data = {
        "comments": "Updated CS review",
        "decision": ReviewDecision.PARTIALLY_APPROVED,
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/reviews/{review_test_ids['review_id']}",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 200
    assert response.json()["decision"] == ReviewDecision.PARTIALLY_APPROVED

def test_add_review_item_cs_user():
    token = get_auth_token(review_test_ids["cs_user"]["email"], review_test_ids["cs_user"]["password"])
    
    # Create form data
    form_data = {
        "item_name": "Medication",
        "requested_amount": 300.00,
        "approved_amount": 250.00,
        "status": ReviewItemStatus.PARTIALLY_APPROVED,
        "rejection_reason": "Partial coverage for this medication"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/reviews/{review_test_ids['review_id']}/items",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 200
    assert response.json()["item_name"] == "Medication"
    assert response.json()["approved_amount"] == 250.00
    assert response.json()["status"] == ReviewItemStatus.PARTIALLY_APPROVED

def test_update_review_item_cs_user():
    token = get_auth_token(review_test_ids["cs_user"]["email"], review_test_ids["cs_user"]["password"])
    
    # Update form data
    form_data = {
        "approved_amount": 300.00,
        "status": ReviewItemStatus.APPROVED,
    }
    
    response = client.put(
        f"{settings.API_V1_STR}/reviews/{review_test_ids['review_id']}/items/{review_test_ids['review_item_id']}",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    assert response.status_code == 200
    assert response.json()["approved_amount"] == 300.00
    assert response.json()["status"] == ReviewItemStatus.APPROVED

# Run tests
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
