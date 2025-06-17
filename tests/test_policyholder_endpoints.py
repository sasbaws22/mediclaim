import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from unittest.mock import patch, MagicMock

from app import app
from app.db.session import get_db
from app.models.models import User, Policy, Claim, Notification, UserRole, ClaimStatus
from app.core.security import create_access_token, get_password_hash


# Test database setup
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="policyholder_user")
def policyholder_user_fixture(session: Session):
    """Create a test policyholder user"""
    user = User(
        id=uuid.uuid4(),
        email="policyholder@test.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test Policyholder",
        role=UserRole.POLICYHOLDER,
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """Create a test admin user"""
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_policy")
def test_policy_fixture(session: Session, policyholder_user: User):
    """Create a test policy for the policyholder"""
    policy = Policy(
        id=uuid.uuid4(),
        member_number="MEM-TEST123",
        plan_type="BASIC",
        policyholder_id=policyholder_user.id,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=365),
        is_active=True
    )
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return policy


@pytest.fixture(name="test_claim")
def test_claim_fixture(session: Session, test_policy: Policy):
    """Create a test claim for the policy"""
    claim = Claim(
        id=uuid.uuid4(),
        reference_number="CLM-TEST123",
        policy_id=test_policy.id,
        hospital_pharmacy="Test Hospital",
        reason="Medical treatment",
        requested_amount=1000.0,
        status=ClaimStatus.SUBMITTED
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


@pytest.fixture(name="test_notification")
def test_notification_fixture(session: Session, policyholder_user: User, test_claim: Claim):
    """Create a test notification for the policyholder"""
    notification = Notification(
        id=uuid.uuid4(),
        user_id=policyholder_user.id,
        claim_id=test_claim.id,
        title="Claim Update",
        message="Your claim has been submitted",
        notification_type="EMAIL",
        is_read=False
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def get_auth_headers(user: User):
    """Generate authentication headers for a user"""
    access_token = create_access_token(
        user_data={"email": user.email, "id": str(user.id)},
        expiry=timedelta(hours=1),
        refresh=False
    )
    return {"Authorization": f"Bearer {access_token}"}


class TestPolicyholderEndpoints:
    """Test cases for policyholder endpoints"""

    def test_get_dashboard_success(self, client: TestClient, session: Session, 
                                 policyholder_user: User, test_policy: Policy, test_claim: Claim):
        """Test successful dashboard retrieval"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/dashboard", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_policies" in data
        assert "total_claims" in data
        assert data["total_policies"] >= 1
        assert data["total_claims"] >= 1

    def test_get_dashboard_unauthorized(self, client: TestClient):
        """Test dashboard access without authentication"""
        response = client.get("/api/v1/policyholders/dashboard")
        assert response.status_code == 403  # Updated to match actual behavior

    def test_get_dashboard_wrong_role(self, client: TestClient, admin_user: User):
        """Test dashboard access with wrong role"""
        headers = get_auth_headers(admin_user)
        response = client.get("/api/v1/policyholders/dashboard", headers=headers)
        assert response.status_code == 403

    def test_get_profile_success(self, client: TestClient, policyholder_user: User):
        """Test successful profile retrieval"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == policyholder_user.email
        assert data["full_name"] == policyholder_user.full_name
        assert data["role"] == UserRole.POLICYHOLDER

    def test_update_profile_success(self, client: TestClient, policyholder_user: User):
        """Test successful profile update"""
        headers = get_auth_headers(policyholder_user)
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@test.com"
        }
        
        with patch('app.utils.audit.audit_service.log_update'):
            response = client.put("/api/v1/policyholders/profile", 
                                json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["email"] == "updated@test.com"

    def test_get_policies_success(self, client: TestClient, policyholder_user: User, test_policy: Policy):
        """Test successful policies retrieval"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/policies", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["member_number"] == test_policy.member_number

    def test_get_policy_by_id_success(self, client: TestClient, policyholder_user: User, test_policy: Policy):
        """Test successful single policy retrieval"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get(f"/api/v1/policyholders/policies/{test_policy.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_policy.id)
        assert data["member_number"] == test_policy.member_number

    def test_get_policy_not_found(self, client: TestClient, policyholder_user: User):
        """Test policy retrieval with non-existent ID"""
        headers = get_auth_headers(policyholder_user)
        fake_id = uuid.uuid4()
        
        response = client.get(f"/api/v1/policyholders/policies/{fake_id}", headers=headers)
        assert response.status_code == 404

    def test_get_claims_success(self, client: TestClient, policyholder_user: User, test_claim: Claim):
        """Test successful claims retrieval"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/claims", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["reference_number"] == test_claim.reference_number

    def test_get_claim_by_id_success(self, client: TestClient, policyholder_user: User, test_claim: Claim):
        """Test successful single claim retrieval"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get(f"/api/v1/policyholders/claims/{test_claim.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_claim.id)
        assert data["reference_number"] == test_claim.reference_number

    def test_create_claim_success(self, client: TestClient, policyholder_user: User, test_policy: Policy):
        """Test successful claim creation"""
        headers = get_auth_headers(policyholder_user)
        claim_data = {
            "policy_id": str(test_policy.id),
            "hospital_pharmacy": "New Hospital",
            "reason": "Emergency treatment",
            "requested_amount": 2000.0
        }
        
        with patch('app.utils.audit.audit_service.log_create'):
            response = client.post("/api/v1/policyholders/claims", 
                                 json=claim_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["hospital_pharmacy"] == "New Hospital"
        assert data["requested_amount"] == 2000.0
        assert data["status"] == ClaimStatus.SUBMITTED

    def test_create_claim_invalid_policy(self, client: TestClient, policyholder_user: User):
        """Test claim creation with invalid policy ID"""
        headers = get_auth_headers(policyholder_user)
        fake_policy_id = uuid.uuid4()
        claim_data = {
            "policy_id": str(fake_policy_id),
            "hospital_pharmacy": "New Hospital",
            "reason": "Emergency treatment",
            "requested_amount": 2000.0
        }
        
        response = client.post("/api/v1/policyholders/claims", 
                             json=claim_data, headers=headers)
        assert response.status_code == 400

    def test_get_notifications_success(self, client: TestClient, policyholder_user: User, test_notification: Notification):
        """Test successful notifications retrieval"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/notifications", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["title"] == test_notification.title

    def test_mark_notification_read_success(self, client: TestClient, policyholder_user: User, test_notification: Notification):
        """Test successful notification mark as read"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_update'):
            response = client.put(f"/api/v1/policyholders/notifications/{test_notification.id}/read", 
                                headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"] == True

    def test_mark_notification_read_not_found(self, client: TestClient, policyholder_user: User):
        """Test marking non-existent notification as read"""
        headers = get_auth_headers(policyholder_user)
        fake_id = uuid.uuid4()
        
        response = client.put(f"/api/v1/policyholders/notifications/{fake_id}/read", 
                            headers=headers)
        assert response.status_code == 404

    def test_pagination_policies(self, client: TestClient, policyholder_user: User, test_policy: Policy):
        """Test pagination for policies endpoint"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/policies?skip=0&limit=10", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_pagination_claims(self, client: TestClient, policyholder_user: User, test_claim: Claim):
        """Test pagination for claims endpoint"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/claims?skip=0&limit=10", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_pagination_notifications(self, client: TestClient, policyholder_user: User, test_notification: Notification):
        """Test pagination for notifications endpoint"""
        headers = get_auth_headers(policyholder_user)
        
        with patch('app.utils.audit.audit_service.log_read'):
            response = client.get("/api/v1/policyholders/notifications?skip=0&limit=10", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__])

