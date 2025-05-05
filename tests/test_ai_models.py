import unittest
import json
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.models import ClaimTriageModel, FraudDetectionModel
from app.ai.document_intelligence import DocumentIntelligence
from app.ai.treatment_analysis import PredictiveCostEstimator, TreatmentAnalyzer
from app.ai.claim_analytics import SmartAssignmentEngine, ClaimLifecycleAnalytics

class TestAIModels(unittest.TestCase):
    """Test cases for AI models in the MedicalClaims backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Initialize models
        self.triage_model = ClaimTriageModel()
        self.fraud_model = FraudDetectionModel()
        self.doc_intelligence = DocumentIntelligence()
        self.cost_estimator = PredictiveCostEstimator()
        self.treatment_analyzer = TreatmentAnalyzer()
        self.assignment_engine = SmartAssignmentEngine()
        self.lifecycle_analytics = ClaimLifecycleAnalytics()
        
        # Create sample data
        self.sample_claim = self._create_sample_claim()
        self.sample_document = self._create_sample_document()
        self.sample_claim_history = self._create_sample_claim_history()
        self.sample_reviewers = self._create_sample_reviewers()
    
    def _create_sample_claim(self):
        """Create a sample claim for testing."""
        return {
            "id": "CLM12345",
            "requested_amount": 5000.0,
            "policy_start_date": (datetime.now() - timedelta(days=180)).isoformat(),
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
        return """
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
        """
    
    def _create_sample_claim_history(self):
        """Create a sample claim history for testing."""
        now = datetime.now()
        return [
            {
                "stage": "submission",
                "status": "submitted",
                "timestamp": (now - timedelta(hours=72)).isoformat(),
                "user_id": "USR001"
            },
            {
                "stage": "triage",
                "status": "in_progress",
                "timestamp": (now - timedelta(hours=70)).isoformat(),
                "user_id": "USR002"
            },
            {
                "stage": "triage",
                "status": "completed",
                "timestamp": (now - timedelta(hours=68)).isoformat(),
                "user_id": "USR002"
            },
            {
                "stage": "review",
                "status": "in_progress",
                "timestamp": (now - timedelta(hours=50)).isoformat(),
                "user_id": "USR003"
            },
            {
                "stage": "review",
                "status": "completed",
                "timestamp": (now - timedelta(hours=30)).isoformat(),
                "user_id": "USR003"
            },
            {
                "stage": "approval",
                "status": "in_progress",
                "timestamp": (now - timedelta(hours=28)).isoformat(),
                "user_id": "USR004"
            },
            {
                "stage": "approval",
                "status": "completed",
                "timestamp": (now - timedelta(hours=24)).isoformat(),
                "user_id": "USR004"
            },
            {
                "stage": "payment",
                "status": "in_progress",
                "timestamp": (now - timedelta(hours=20)).isoformat(),
                "user_id": "USR005"
            },
            {
                "stage": "payment",
                "status": "completed",
                "timestamp": (now - timedelta(hours=10)).isoformat(),
                "user_id": "USR005"
            }
        ]
    
    def _create_sample_reviewers(self):
        """Create sample reviewers for testing."""
        return [
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
    
    def test_claim_triage_model(self):
        """Test the claim triage model."""
        # Since the model is not trained, it should use rule-based triage
        # We'll mock the training by setting is_trained to True
        self.triage_model.is_trained = True
        
        # Test prediction
        results = self.triage_model.predict_priority([self.sample_claim])
        
        # Verify results
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)
        self.assertIn('priority', results[0])
        self.assertIn('processing_path', results[0])
        self.assertIn('estimated_processing_time', results[0])
        
        # Reset model state
        self.triage_model.is_trained = False
    
    def test_fraud_detection_model(self):
        """Test the fraud detection model."""
        # Since the model is not trained, it should use rule-based detection
        # We'll mock the training by setting is_trained to True
        self.fraud_model.is_trained = True
        
        # Test prediction
        results = self.fraud_model.predict_fraud([self.sample_claim])
        
        # Verify results
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)
        self.assertIn('fraud_probability', results[0])
        self.assertIn('red_flags', results[0])
        self.assertIn('recommended_action', results[0])
        
        # Reset model state
        self.fraud_model.is_trained = False
    
    def test_document_intelligence(self):
        """Test the document intelligence system."""
        # Process the sample document
        extracted_data = self.doc_intelligence.process_document(self.sample_document)
        
        # Verify results
        self.assertIsNotNone(extracted_data)
        self.assertIn('entities', extracted_data)
        self.assertIn('category', extracted_data)
        self.assertIn('key_values', extracted_data)
        self.assertIn('confidence', extracted_data)
        
        # Test claim details extraction
        claim_details = self.doc_intelligence.extract_claim_details(self.sample_document)
        
        # Verify results
        self.assertIsNotNone(claim_details)
        self.assertIn('diagnoses', claim_details)
        self.assertIn('treatments', claim_details)
        self.assertIn('providers', claim_details)
        self.assertIn('dates', claim_details)
        self.assertIn('amounts', claim_details)
    
    def test_cost_estimator(self):
        """Test the predictive cost estimator."""
        # Since the model is not trained, it should raise an error
        # We'll mock the training by setting is_trained to True
        self.cost_estimator.is_trained = True
        
        # Test prediction
        results = self.cost_estimator.predict_cost([self.sample_claim])
        
        # Verify results
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)
        self.assertIn('initial_amount', results[0])
        self.assertIn('predicted_final_amount', results[0])
        self.assertIn('confidence_interval', results[0])
        self.assertIn('key_factors', results[0])
        
        # Reset model state
        self.cost_estimator.is_trained = False
    
    def test_treatment_analyzer(self):
        """Test the treatment appropriateness analyzer."""
        # Analyze treatments in the sample claim
        results = self.treatment_analyzer.analyze_claim_treatments(self.sample_claim)
        
        # Verify results
        self.assertIsNotNone(results)
        self.assertIn('overall_appropriateness', results)
        self.assertIn('treatments_analyzed', results)
        self.assertIn('treatment_analyses', results)
        
        # Verify individual treatment analyses
        if results['treatments_analyzed'] > 0:
            treatment_analysis = results['treatment_analyses'][0]
            self.assertIn('appropriateness_score', treatment_analysis)
            self.assertIn('is_appropriate', treatment_analysis)
            self.assertIn('issues', treatment_analysis)
    
    def test_assignment_engine(self):
        """Test the smart assignment engine."""
        # Since the model is not trained, it should use rule-based assignment
        # We'll test the rule-based assignment
        
        # Test recommendation
        results = self.assignment_engine.recommend_reviewers(self.sample_claim, self.sample_reviewers)
        
        # Verify results
        self.assertIsNotNone(results)
        self.assertEqual(len(results), len(self.sample_reviewers))
        self.assertIn('reviewer_id', results[0])
        self.assertIn('success_probability', results[0])
        self.assertIn('expected_processing_time', results[0])
        self.assertIn('expertise_match', results[0])
    
    def test_lifecycle_analytics(self):
        """Test the claim lifecycle analytics."""
        # Analyze the sample claim history
        results = self.lifecycle_analytics.analyze_claim_lifecycle(self.sample_claim_history)
        
        # Verify results
        self.assertIsNotNone(results)
        self.assertIn('total_processing_time', results)
        self.assertIn('bottlenecks', results)
        self.assertIn('optimization_opportunities', results)
        self.assertIn('stage_metrics', results)
        
        # Test batch analysis
        batch_results = self.lifecycle_analytics.analyze_claims_batch([
            {"history": self.sample_claim_history}
        ])
        
        # Verify batch results
        self.assertIsNotNone(batch_results)
        self.assertIn('average_processing_time', batch_results)
        self.assertIn('system_bottlenecks', batch_results)
        self.assertIn('stage_metrics', batch_results)
        self.assertIn('recommendations', batch_results)

if __name__ == '__main__':
    unittest.main()
