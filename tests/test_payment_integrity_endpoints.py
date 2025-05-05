import unittest
import json
import os
import sys
from fastapi.testclient import TestClient

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from app.core.security import create_access_token
from app.models.models import UserRole

class TestEligibilityEndpoints(unittest.TestCase):
    """Test cases for the Eligibility Verification API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Create test tokens for different user roles
        self.admin_token = self._create_test_token(role=UserRole.ADMIN)
        self.processor_token = self._create_test_token(role=UserRole.CLAIMS_PROCESSOR)
        self.customer_service_token = self._create_test_token(role=UserRole.CUSTOMER_SERVICE)
        self.provider_token = self._create_test_token(role=UserRole.PROVIDER)
        self.user_token = self._create_test_token(role=UserRole.USER)
        
        # Create sample test data
        self.sample_eligibility_request = {
            "member_id": "M12345",
            "service_date": "2025-04-12",
            "provider_id": "P12345",
            "service_codes": ["99201", "99202"]
        }
        
        self.sample_batch_request = {
            "verification_requests": [
                {
                    "member_id": "M12345",
                    "service_date": "2025-04-12",
                    "provider_id": "P12345",
                    "service_codes": ["99201"]
                },
                {
                    "member_id": "M67890",
                    "service_date": "2025-04-12",
                    "provider_id": "P12345",
                    "service_codes": ["99202"]
                }
            ]
        }
    
    def _create_test_token(self, role):
        """Create a test JWT token for a specific role."""
        token_data = {
            "sub": f"test_{role.lower()}@example.com",
            "role": role
        }
        return create_access_token(token_data)
    
    def test_verify_eligibility_endpoint(self):
        """Test the eligibility verification endpoint."""
        # Test with claims processor role
        response = self.client.post(
            "/api/eligibility/verify",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=self.sample_eligibility_request
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("verification_result", data)
        
        # Verify verification result structure
        result = data["verification_result"]
        self.assertIn("is_eligible", result)
        self.assertIn("status", result)
        self.assertIn("member", result)
        self.assertIn("provider", result)
        self.assertIn("service_coverage", result)
        
        # Test with customer service role
        response = self.client.post(
            "/api/eligibility/verify",
            headers={"Authorization": f"Bearer {self.customer_service_token}"},
            json=self.sample_eligibility_request
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Test with provider role
        response = self.client.post(
            "/api/eligibility/verify",
            headers={"Authorization": f"Bearer {self.provider_token}"},
            json=self.sample_eligibility_request
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/eligibility/verify",
            headers={"Authorization": f"Bearer {self.user_token}"},
            json=self.sample_eligibility_request
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_verify_eligibility_missing_fields(self):
        """Test eligibility verification with missing required fields."""
        # Create request with missing fields
        incomplete_request = {
            "member_id": "M12345",
            "service_date": "2025-04-12"
            # Missing provider_id and service_codes
        }
        
        response = self.client.post(
            "/api/eligibility/verify",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=incomplete_request
        )
        
        # Verify bad request response
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("Missing required fields", data["detail"])
    
    def test_batch_verify_eligibility_endpoint(self):
        """Test the batch eligibility verification endpoint."""
        # Test with claims processor role
        response = self.client.post(
            "/api/eligibility/batch-verify",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=self.sample_batch_request
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("batch_results", data)
        self.assertIn("total_requests", data)
        self.assertIn("successful_verifications", data)
        
        # Verify batch results
        batch_results = data["batch_results"]
        self.assertEqual(len(batch_results), 2)
        
        # Test with admin role
        response = self.client.post(
            "/api/eligibility/batch-verify",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json=self.sample_batch_request
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/eligibility/batch-verify",
            headers={"Authorization": f"Bearer {self.customer_service_token}"},
            json=self.sample_batch_request
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_clear_eligibility_cache_endpoint(self):
        """Test the clear eligibility cache endpoint."""
        # Test with admin role
        response = self.client.post(
            "/api/eligibility/clear-cache",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/eligibility/clear-cache",
            headers={"Authorization": f"Bearer {self.processor_token}"}
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)


class TestPaymentIntegrityEndpoints(unittest.TestCase):
    """Test cases for the Payment Integrity Analysis API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Create test tokens for different user roles
        self.admin_token = self._create_test_token(role=UserRole.ADMIN)
        self.processor_token = self._create_test_token(role=UserRole.CLAIMS_PROCESSOR)
        self.auditor_token = self._create_test_token(role=UserRole.CLAIMS_AUDITOR)
        self.analyst_token = self._create_test_token(role=UserRole.FINANCIAL_ANALYST)
        self.user_token = self._create_test_token(role=UserRole.USER)
        
        # Create sample test data
        self.sample_claim = {
            "claim_id": "CLM12345",
            "member_id": "M12345",
            "provider_id": "P12345",
            "service_date": "2025-04-12",
            "submission_date": "2025-04-12",
            "requested_amount": 1000.00,
            "service_count": 5,
            "diagnosis_count": 2,
            "diagnosis_codes": ["J18.9", "R05"],
            "procedure_codes": ["99213", "71045", "94640"],
            "modifiers": []
        }
        
        self.sample_batch_request = {
            "claims": [
                self.sample_claim,
                {
                    "claim_id": "CLM67890",
                    "member_id": "M67890",
                    "provider_id": "P67890",
                    "service_date": "2025-04-12",
                    "submission_date": "2025-04-12",
                    "requested_amount": 2000.00,
                    "service_count": 3,
                    "diagnosis_count": 1,
                    "diagnosis_codes": ["I10"],
                    "procedure_codes": ["99214", "93000"],
                    "modifiers": []
                }
            ]
        }
        
        self.sample_training_data = {
            "claims_data": [self.sample_claim for _ in range(10)],
            "model_path": "/tmp/payment_integrity_model.joblib"
        }
    
    def _create_test_token(self, role):
        """Create a test JWT token for a specific role."""
        token_data = {
            "sub": f"test_{role.lower()}@example.com",
            "role": role
        }
        return create_access_token(token_data)
    
    def test_analyze_claim_integrity_endpoint(self):
        """Test the payment integrity analysis endpoint."""
        # Test with claims processor role
        response = self.client.post(
            "/api/payment-integrity/analyze",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=self.sample_claim
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("analysis_result", data)
        
        # Verify analysis result structure
        result = data["analysis_result"]
        self.assertIn("claim_id", result)
        self.assertIn("analysis_id", result)
        self.assertIn("risk_score", result)
        self.assertIn("issues", result)
        self.assertIn("recommended_action", result)
        self.assertIn("potential_savings", result)
        
        # Test with claims auditor role
        response = self.client.post(
            "/api/payment-integrity/analyze",
            headers={"Authorization": f"Bearer {self.auditor_token}"},
            json=self.sample_claim
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Test with financial analyst role
        response = self.client.post(
            "/api/payment-integrity/analyze",
            headers={"Authorization": f"Bearer {self.analyst_token}"},
            json=self.sample_claim
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/payment-integrity/analyze",
            headers={"Authorization": f"Bearer {self.user_token}"},
            json=self.sample_claim
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_batch_analyze_claims_endpoint(self):
        """Test the batch payment integrity analysis endpoint."""
        # Test with claims processor role
        response = self.client.post(
            "/api/payment-integrity/batch-analyze",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=self.sample_batch_request
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("batch_results", data)
        self.assertIn("summary", data)
        
        # Verify batch results
        batch_results = data["batch_results"]
        self.assertEqual(len(batch_results), 2)
        
        # Verify summary
        summary = data["summary"]
        self.assertIn("total_claims", summary)
        self.assertIn("successful_analyses", summary)
        self.assertIn("total_potential_savings", summary)
        
        # Test with claims auditor role
        response = self.client.post(
            "/api/payment-integrity/batch-analyze",
            headers={"Authorization": f"Bearer {self.auditor_token}"},
            json=self.sample_batch_request
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/payment-integrity/batch-analyze",
            headers={"Authorization": f"Bearer {self.user_token}"},
            json=self.sample_batch_request
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_train_payment_integrity_model_endpoint(self):
        """Test the payment integrity model training endpoint."""
        # Test with admin role
        response = self.client.post(
            "/api/payment-integrity/train",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json=self.sample_training_data
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("is_trained", data)
        self.assertTrue(data["is_trained"])
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/payment-integrity/train",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=self.sample_training_data
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()
