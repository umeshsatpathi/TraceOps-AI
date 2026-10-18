import unittest

from action_policy import choose_safe_action


class ActionPolicyTests(unittest.TestCase):
    def test_remediated_bola_uses_regression_check(self):
        context = {
            "finding": {"id": "F-004", "type": "BOLA", "status": "REMEDIATED"},
            "priority": {"priority_score": 90},
            "impact_paths": [{"asset": "Customer Orders", "classification": "sensitive"}],
            "correlated_findings": [{"finding_id": "F-001"}],
        }
        action = choose_safe_action(context)
        self.assertEqual(action["action_kind"], "RUN_SYNTHETIC_BOLA_CHECK")
        self.assertIn("regression", action["reason"].lower())

    def test_csp_uses_header_rescan(self):
        context = {
            "finding": {"id": "F-003", "type": "MISSING_CSP", "status": "UNVERIFIED"},
            "priority": {"priority_score": 41},
            "impact_paths": [{"asset": None, "classification": None}],
            "correlated_findings": [],
        }
        action = choose_safe_action(context)
        self.assertEqual(action["action_kind"], "RUN_HTTP_HEADER_RESCAN")

    def test_unknown_type_never_executes_arbitrary_command(self):
        context = {
            "finding": {"id": "F-X", "type": "UNKNOWN", "status": "UNVERIFIED"},
            "priority": {"priority_score": 10},
            "impact_paths": [],
            "correlated_findings": [],
        }
        action = choose_safe_action(context)
        self.assertEqual(action["action_kind"], "REVIEW_ONLY")
        self.assertEqual(action["execution_mode"], "NO_AUTOMATED_EXECUTION")


if __name__ == "__main__":
    unittest.main()
