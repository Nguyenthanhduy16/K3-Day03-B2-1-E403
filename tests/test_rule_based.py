"""Tests for the deterministic Level 1 expense route."""

import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app import execute_tool  # noqa: E402
from debug_dashboard import answer_question  # noqa: E402
from rule_based import run_rule_based  # noqa: E402


class ExplodingProvider:
    """Fails immediately if Level 1 accidentally invokes an LLM."""

    model_name = "must-not-run"

    def generate(self, prompt, system_prompt=""):
        raise AssertionError("Rule-based mode must not call the LLM")


class RuleBasedTests(unittest.TestCase):
    def test_full_approval_request_uses_fixed_tool_order(self):
        result = run_rule_based(
            "Nhân viên E102 đề nghị 12000000 VND loại client_event, "
            "có hóa đơn. Hãy kiểm tra phê duyệt.",
            execute_tool,
        )

        self.assertTrue(result["answer"].startswith("ESCALATE"))
        self.assertEqual(
            result["tools_used"],
            [
                "get_employee_profile",
                "get_expense_policy",
                "check_department_budget",
                "get_approval_route",
            ],
        )

    def test_negative_amount_is_rejected_without_tool(self):
        result = run_rule_based(
            "Duyệt -5000000 VND loại meal không có hóa đơn.",
            execute_tool,
        )

        self.assertTrue(result["answer"].startswith("REJECT"))
        self.assertEqual(result["tools_used"], [])

    def test_policy_question_stops_after_policy_tool(self):
        result = run_rule_based(
            "Khoản 800000 VND loại meal có hóa đơn có phù hợp chính sách không?",
            execute_tool,
        )

        self.assertTrue(result["answer"].startswith("INFORMATION"))
        self.assertEqual(result["tools_used"], ["get_expense_policy"])

    def test_dashboard_rule_mode_never_calls_provider(self):
        result = answer_question(
            "Nhân viên E102 đề nghị 12000000 VND loại client_event, "
            "có hóa đơn. Hãy kiểm tra phê duyệt.",
            "rule_based",
            ExplodingProvider(),
        )

        self.assertEqual(result["route"], "RULE_BASED")
        self.assertEqual(result["provider"], "Local Rules")
        self.assertEqual(result["model"], "rule-engine-v1")


if __name__ == "__main__":
    unittest.main()
