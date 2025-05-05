import unittest
import json
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.payment_integrity import EligibilityVerificationService, PaymentIntegrityAnalyzer

class TestEligibilityVerification(unittest.TestCase):
    """Test cases for the Eligibility Verification Service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.eligibility_service = EligibilityVerificationService()
        
        # Create sample test data
        self.sample_member_id = "M12345"
        self.sample_provider_id = "P12345"
        self.sample_service_date = datetime.now().strftime("%Y-%m-%d")
        self.sample_service_codes = ["99201", "99202"]
        self.sample_policy_id = "POL001"
    
    def test_verify_eligibility_active_member(self):
        """Test eligibility verification for an active member."""
        # Verify eligibility
        result = self.eligibility_service.verify_eligibility(
            member_id=self.sample_member_id,
            service_date=self.sample_service_date,
            provider_id=self.sample_provider_id,
            service_codes=self.sample_service_codes,
            policy_id=self.sample_policy_id
        )
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIn("is_eligible", result)
        self.assertIn("status", result)
        self.assertIn("verification_id", result)
        self.assertIn("timestamp", result)
        self.assertIn("member", result)
        self.assertIn("provider", result)
        self.assertIn("service_coverage", result)
        self.assertIn("member_responsibility", result)
        
        # Verify member is eligible
        self.assertTrue(result["is_eligible"])
        self.assertEqual(result["status"], "ACTIVE")
        
        # Verify member details
        self.assertEqual(result["member"]["member_id"], self.sample_member_id)
        self.assertEqual(result["member"]["policy_id"], self.sample_policy_id)
        
        # Verify provider details
        self.assertEqual(result["provider"]["provider_id"], self.sample_provider_id)
        self.assertTrue(result["provider"]["in_network"])
        
        # Verify service coverage
        self.assertEqual(len(result["service_coverage"]), len(self.sample_service_codes))
        for service in result["service_coverage"]:
            self.assertIn("service_code", service)
            self.assertIn("covered", service)
            self.assertIn(service["service_code"], self.sample_service_codes)
        
        # Verify member responsibility
        self.assertIn("total_estimated_cost", result["member_responsibility"])
        self.assertIn("member_responsibility", result["member_responsibility"])
        self.assertIn("deductible", result["member_responsibility"])
        self.assertIn("deductible_met", result["member_responsibility"])
    
    def test_verify_eligibility_inactive_member(self):
        """Test eligibility verification for an inactive member."""
        # Verify eligibility for a termed member
        result = self.eligibility_service.verify_eligibility(
            member_id="M67890",  # Termed member
            service_date=self.sample_service_date,
            provider_id=self.sample_provider_id,
            service_codes=self.sample_service_codes
        )
        
        # Verify member is not eligible
        self.assertFalse(result["is_eligible"])
        self.assertEqual(result["status"], "INACTIVE")
    
    def test_verify_eligibility_out_of_network_provider(self):
        """Test eligibility verification with an out-of-network provider."""
        # Verify eligibility with out-of-network provider
        result = self.eligibility_service.verify_eligibility(
            member_id=self.sample_member_id,
            service_date=self.sample_service_date,
            provider_id="P67890",  # Out-of-network provider
            service_codes=self.sample_service_codes,
            policy_id=self.sample_policy_id
        )
        
        # Verify result
        self.assertFalse(result["is_eligible"])
        self.assertEqual(result["provider"]["network_status"], "OUT_OF_NETWORK")
        self.assertFalse(result["provider"]["in_network"])
        
        # Verify warnings
        self.assertIn("warnings", result)
        self.assertTrue(any("OUT_OF_NETWORK" in warning.get("code", "") for warning in result["warnings"]))
    
    def test_verify_eligibility_non_covered_service(self):
        """Test eligibility verification with a non-covered service."""
        # Verify eligibility with non-covered service
        result = self.eligibility_service.verify_eligibility(
            member_id=self.sample_member_id,
            service_date=self.sample_service_date,
            provider_id=self.sample_provider_id,
            service_codes=["J0131"],  # Non-covered service
            policy_id=self.sample_policy_id
        )
        
        # Verify service coverage
        self.assertEqual(len(result["service_coverage"]), 1)
        self.assertFalse(result["service_coverage"][0]["covered"])
        
        # Verify warnings
        self.assertIn("warnings", result)
        self.assertTrue(any("SERVICE_NOT_COVERED" in warning.get("code", "") for warning in result["warnings"]))
    
    def test_eligibility_cache(self):
        """Test that eligibility results are cached."""
        # First verification
        result1 = self.eligibility_service.verify_eligibility(
            member_id=self.sample_member_id,
            service_date=self.sample_service_date,
            provider_id=self.sample_provider_id,
            service_codes=self.sample_service_codes,
            policy_id=self.sample_policy_id
        )
        
        # Second verification (should use cache)
        result2 = self.eligibility_service.verify_eligibility(
            member_id=self.sample_member_id,
            service_date=self.sample_service_date,
            provider_id=self.sample_provider_id,
            service_codes=self.sample_service_codes,
            policy_id=self.sample_policy_id
        )
        
        # Verify both results have the same verification ID (indicating cache hit)
        self.assertEqual(result1["verification_id"], result2["verification_id"])
        
        # Clear cache
        self.eligibility_service.clear_cache()
        
        # Third verification (should not use cache)
        result3 = self.eligibility_service.verify_eligibility(
            member_id=self.sample_member_id,
            service_date=self.sample_service_date,
            provider_id=self.sample_provider_id,
            service_codes=self.sample_service_codes,
            policy_id=self.sample_policy_id
        )
        
        # Verify different verification ID (indicating cache miss)
        self.assertNotEqual(result1["verification_id"], result3["verification_id"])


class TestPaymentIntegrityAnalyzer(unittest.TestCase):
    """Test cases for the Payment Integrity Analyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.payment_integrity_analyzer = PaymentIntegrityAnalyzer()
        
        # Create sample test data
        self.sample_claim = {
            "claim_id": "CLM12345",
            "member_id": "M12345",
            "provider_id": "P12345",
            "service_date": datetime.now().strftime("%Y-%m-%d"),
            "submission_date": datetime.now().strftime("%Y-%m-%d"),
            "requested_amount": 1000.00,
            "service_count": 5,
            "diagnosis_count": 2,
            "diagnosis_codes": ["J18.9", "R05"],
            "procedure_codes": ["99213", "71045", "94640"],
            "modifiers": []
        }
        
        self.duplicate_claim = {
            "claim_id": "CLM67890",
            "member_id": "M12345",
            "provider_id": "P12345",
            "service_date": datetime.now().strftime("%Y-%m-%d"),
            "submission_date": datetime.now().strftime("%Y-%m-%d"),
            "requested_amount": 1000.00,
            "service_count": 5,
            "diagnosis_count": 2,
            "diagnosis_codes": ["J18.9", "R05"],
            "procedure_codes": ["99213", "71045", "94640"],
            "modifiers": [],
            "previous_claims": [self.sample_claim]
        }
        
        self.high_amount_claim = {
            "claim_id": "CLM24680",
            "member_id": "M12345",
            "provider_id": "P12345",
            "service_date": datetime.now().strftime("%Y-%m-%d"),
            "submission_date": datetime.now().strftime("%Y-%m-%d"),
            "requested_amount": 100000.00,
            "service_count": 5,
            "diagnosis_count": 2,
            "diagnosis_codes": ["J18.9", "R05"],
            "procedure_codes": ["99213", "71045", "94640"],
            "modifiers": []
        }
        
        self.unbundling_claim = {
            "claim_id": "CLM13579",
            "member_id": "M12345",
            "provider_id": "P12345",
            "service_date": datetime.now().strftime("%Y-%m-%d"),
            "submission_date": datetime.now().strftime("%Y-%m-%d"),
            "requested_amount": 2000.00,
            "service_count": 5,
            "diagnosis_count": 2,
            "diagnosis_codes": ["I10", "E11.9"],
            "procedure_codes": ["80053", "84443"],
            "modifiers": []
        }
    
    def test_analyze_claim_normal(self):
        """Test payment integrity analysis for a normal claim."""
        # Analyze claim
        result = self.payment_integrity_analyzer.analyze_claim(self.sample_claim)
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIn("claim_id", result)
        self.assertIn("analysis_id", result)
        self.assertIn("timestamp", result)
        self.assertIn("risk_score", result)
        self.assertIn("issues_detected", result)
        self.assertIn("issues", result)
        self.assertIn("recommended_action", result)
        self.assertIn("potential_savings", result)
        
        # Verify claim ID
        self.assertEqual(result["claim_id"], self.sample_claim["claim_id"])
        
        # Verify risk score is between 0 and 1
        self.assertGreaterEqual(result["risk_score"], 0)
        self.assertLessEqual(result["risk_score"], 1)
        
        # Verify recommended action
        self.assertIn("action", result["recommended_action"])
        self.assertIn("reason", result["recommended_action"])
        self.assertIn("priority", result["recommended_action"])
    
    def test_analyze_claim_duplicate(self):
        """Test payment integrity analysis for a duplicate claim."""
        # Analyze claim
        result = self.payment_integrity_analyzer.analyze_claim(self.duplicate_claim)
        
        # Verify duplicate detection
        self.assertTrue(result["issues_detected"])
        self.assertTrue(any("POTENTIAL_DUPLICATE" in issue.get("type", "") for issue in result["issues"]))
        
        # Verify duplicate probability
        self.assertGreater(result["duplicate_probability"], 0.5)
        
        # Verify recommended action
        self.assertEqual(result["recommended_action"]["action"], "HOLD_FOR_REVIEW")
        self.assertEqual(result["recommended_action"]["priority"], "HIGH")
        
        # Verify potential savings
        self.assertEqual(result["potential_savings"]["duplicate_prevention"], self.duplicate_claim["requested_amount"])
    
    def test_analyze_claim_high_amount(self):
        """Test payment integrity analysis for a claim with unusually high amount."""
        # Analyze claim
        result = self.payment_integrity_analyzer.analyze_claim(self.high_amount_claim)
        
        # Verify high amount detection
        self.assertTrue(result["issues_detected"])
        self.assertTrue(any("HIGH_DOLLAR_AMOUNT" in issue.get("type", "") for issue in result["issues"]))
        
        # Verify risk score is higher
        self.assertGreater(result["risk_score"], 0.3)
        
        # Verify recommended action
        self.assertIn(result["recommended_action"]["action"], ["HOLD_FOR_REVIEW", "FLAG_FOR_REVIEW"])
    
    def test_analyze_claim_unbundling(self):
        """Test payment integrity analysis for a claim with potential unbundling."""
        # Analyze claim
        result = self.payment_integrity_analyzer.analyze_claim(self.unbundling_claim)
        
        # Verify unbundling detection
        self.assertTrue(result["issues_detected"])
        self.assertTrue(any("POTENTIAL_UNBUNDLING" in issue.get("type", "") for issue in result["issues"]))
        
        # Verify coding correction savings
        self.assertGreater(result["potential_savings"]["coding_correction"], 0)
    
    def test_model_training(self):
        """Test training the payment integrity model."""
        # Create training data
        training_claims = [self.sample_claim.copy() for _ in range(10)]
        
        # Add some variations
        for i, claim in enumerate(training_claims):
            claim["claim_id"] = f"CLM{i+1:05d}"
            claim["requested_amount"] = 1000.00 + (i * 100)
            claim["service_count"] = 5 + (i % 3)
        
        # Train the model
        self.payment_integrity_analyzer.train(training_claims)
        
        # Verify model is trained
        self.assertTrue(self.payment_integrity_analyzer.is_trained)
        
        # Analyze a claim with the trained model
        result = self.payment_integrity_analyzer.analyze_claim(self.sample_claim)
        
        # Verify analysis still works
        self.assertIsNotNone(result)
        self.assertIn("risk_score", result)


if __name__ == '__main__':
    unittest.main()
