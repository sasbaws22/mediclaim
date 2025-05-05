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

class TestAIEndpoints(unittest.TestCase):
    """Test cases for AI endpoints in the MedicalClaims backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Create test tokens for different user roles
        self.admin_token = self._create_test_token(role=UserRole.ADMIN)
        self.processor_token = self._create_test_token(role=UserRole.CLAIMS_PROCESSOR)
        self.reviewer_token = self._create_test_token(role=UserRole.REVIEWER)
        self.investigator_token = self._create_test_token(role=UserRole.FRAUD_INVESTIGATOR)
        self.manager_token = self._create_test_token(role=UserRole.CLAIMS_MANAGER)
        
        # Create sample data
        self.sample_claim = self._create_sample_claim()
        self.sample_document = self._create_sample_document()
        self.sample_claim_history = self._create_sample_claim_history()
        self.sample_reviewers = self._create_sample_reviewers()
    
    def _create_test_token(self, role):
        """Create a test JWT token for a specific role."""
        token_data = {
            "sub": f"test_{role.lower()}@example.com",
            "role": role
        }
        return create_access_token(token_data)
    
    def _create_sample_claim(self):
        """Create a sample claim for testing."""
        return {
            "id": "CLM12345",
            "requested_amount": 5000.0,
            "policy_start_date": "2024-10-15T00:00:00",
            "claimant_history_count": 2,
            "provider_history_count": 15,
            "diagnosis_risk_score": 0.6,
            "treatment_complexity_score": 0.7,
            "is_emergency": False,
            "documentation_completeness": 0.8,
            "geographic_risk_score": 0.3,
            "temporal_anomaly_score": 0.2,
            "service_frequency_score": 0.4,
            "diagnosis_treatment_match_score": 0.9,
            "claimant_age": 45,
            "is_inpatient": True,
            "expected_recovery_time": 21,
            "diagnosis": "bacterial pneumonia",
            "treatments": ["antibiotics", "pain_medication"],
            "patient": {
                "age": 45,
                "allergies": ["penicillin"]
            },
            "claim_type_id": 2
        }
    
    def _create_sample_document(self):
        """Create a sample medical document for testing."""
        return {
            "text": """
            MEDICAL REPORT
            
            Patient: John Doe
            Date of Service: 2025-03-15
            
            Diagnosis: Bacterial pneumonia
            
            Treatment: The patient was prescribed antibiotics (amoxicillin 500mg) to be taken
            three times daily for 10 days. Pain medication (acetaminophen 500mg) was also
            prescribed for fever and discomfort.
            
            Provider: Dr. Jane Smith, Pulmonology
            Hospital: City General Hospital
            
            Follow-up appointment scheduled for: 2025-03-25
            
            Amount billed: $5,000.00
            """,
            "policy_data": {
                "covered_treatments": ["antibiotics", "pain medication"],
                "start_date": "2024-01-01",
                "end_date": "2025-12-31"
            }
        }
    
    def _create_sample_claim_history(self):
        """Create a sample claim history for testing."""
        return {
            "history": [
                {
                    "stage": "submission",
                    "status": "submitted",
                    "timestamp": "2025-04-09T10:00:00",
                    "user_id": "USR001"
                },
                {
                    "stage": "triage",
                    "status": "in_progress",
                    "timestamp": "2025-04-09T12:00:00",
                    "user_id": "USR002"
                },
                {
                    "stage": "triage",
                    "status": "completed",
                    "timestamp": "2025-04-09T14:00:00",
                    "user_id": "USR002"
                },
                {
                    "stage": "review",
                    "status": "in_progress",
                    "timestamp": "2025-04-10T09:00:00",
                    "user_id": "USR003"
                },
                {
                    "stage": "review",
                    "status": "completed",
                    "timestamp": "2025-04-11T09:00:00",
                    "user_id": "USR003"
                },
                {
                    "stage": "approval",
                    "status": "in_progress",
                    "timestamp": "2025-04-11T11:00:00",
                    "user_id": "USR004"
                },
                {
                    "stage": "approval",
                    "status": "completed",
                    "timestamp": "2025-04-11T15:00:00",
                    "user_id": "USR004"
                },
                {
                    "stage": "payment",
                    "status": "in_progress",
                    "timestamp": "2025-04-11T16:00:00",
                    "user_id": "USR005"
                },
                {
                    "stage": "payment",
                    "status": "completed",
                    "timestamp": "2025-04-12T10:00:00",
                    "user_id": "USR005"
                }
            ]
        }
    
    def _create_sample_reviewers(self):
        """Create sample reviewers for testing."""
        return {
            "claim": self.sample_claim,
            "available_reviewers": [
                {
                    "id": "REV001",
                    "name": "Dr. Smith",
                    "expertise_level": 0.9,
                    "specialty_id": 2,
                    "years_experience": 10,
                    "current_workload": 5,
                    "avg_processing_time": 12,
                    "success_rate": 0.95
                },
                {
                    "id": "REV002",
                    "name": "Dr. Johnson",
                    "expertise_level": 0.7,
                    "specialty_id": 1,
                    "years_experience": 5,
                    "current_workload": 3,
                    "avg_processing_time": 18,
                    "success_rate": 0.85
                },
                {
                    "id": "REV003",
                    "name": "Dr. Williams",
                    "expertise_level": 0.8,
                    "specialty_id": 2,
                    "years_experience": 7,
                    "current_workload": 8,
                    "avg_processing_time": 15,
                    "success_rate": 0.9
                }
            ]
        }
    
    def test_triage_endpoint(self):
        """Test the claim triage endpoint."""
        # Test with claims processor role
        response = self.client.post(
            "/api/ai/triage",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=self.sample_claim
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("triage_result", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/triage",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json=self.sample_claim
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_fraud_detection_endpoint(self):
        """Test the fraud detection endpoint."""
        # Test with fraud investigator role
        response = self.client.post(
            "/api/ai/fraud-detection",
            headers={"Authorization": f"Bearer {self.investigator_token}"},
            json=self.sample_claim
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("fraud_analysis", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/fraud-detection",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json=self.sample_claim
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_document_analysis_endpoint(self):
        """Test the document analysis endpoint."""
        # Test with claims processor role
        response = self.client.post(
            "/api/ai/document-analysis",
            headers={"Authorization": f"Bearer {self.processor_token}"},
            json=self.sample_document
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("extracted_data", data)
        self.assertIn("validation_results", data)
        self.assertIn("claim_details", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/document-analysis",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json=self.sample_document
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_cost_estimation_endpoint(self):
        """Test the cost estimation endpoint."""
        # Test with reviewer role
        response = self.client.post(
            "/api/ai/cost-estimation",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
            json=self.sample_claim
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("cost_estimation", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/cost-estimation",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json=self.sample_claim
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_treatment_analysis_endpoint(self):
        """Test the treatment analysis endpoint."""
        # Test with reviewer role
        response = self.client.post(
            "/api/ai/treatment-analysis",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
            json=self.sample_claim
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("treatment_analysis", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/treatment-analysis",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json=self.sample_claim
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_reviewer_assignment_endpoint(self):
        """Test the reviewer assignment endpoint."""
        # Test with claims manager role
        response = self.client.post(
            "/api/ai/reviewer-assignment",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json=self.sample_reviewers
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("recommendations", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/reviewer-assignment",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json=self.sample_reviewers
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_lifecycle_analysis_endpoint(self):
        """Test the lifecycle analysis endpoint."""
        # Test with claims manager role
        response = self.client.post(
            "/api/ai/lifecycle-analysis",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json=self.sample_claim_history
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("lifecycle_analysis", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/lifecycle-analysis",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json=self.sample_claim_history
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_batch_analysis_endpoint(self):
        """Test the batch analysis endpoint."""
        # Test with claims manager role
        response = self.client.post(
            "/api/ai/batch-analysis",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={"claims": [{"history": self.sample_claim_history["history"]}]}
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("batch_analysis", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/batch-analysis",
            headers={"Authorization": f"Bearer {self._create_test_token(role='user')}"},
            json={"claims": [{"history": self.sample_claim_history["history"]}]}
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)
    
    def test_train_models_endpoint(self):
        """Test the model training endpoint."""
        # Test with admin role
        training_data = {
            "triage_data": {
                "claims": [self.sample_claim],
                "priorities": [2]
            },
            "fraud_data": {
                "claims": [self.sample_claim],
                "fraud_labels": [0]
            }
        }
        
        response = self.client.post(
            "/api/ai/train-models",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json=training_data
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("training_results", data)
        
        # Test with unauthorized role
        response = self.client.post(
            "/api/ai/train-models",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json=training_data
        )
        
        # Verify unauthorized response
        self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()
