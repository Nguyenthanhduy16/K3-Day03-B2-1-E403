"""Safety tests for the interactive expense-agent dashboard."""

import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from debug_dashboard import run_debug_react  # noqa: E402


class HumanApprovalProvider:
    """Model stub that incorrectly approves after collecting valid evidence."""

    def generate(self, prompt, system_prompt=""):
        if "Action: get_employee_profile" not in prompt:
            return (
                "Thought: Xác minh nhân viên.\n"
                'Action: get_employee_profile({"employee_id": "E102"})'
            )
        if "Action: get_expense_policy" not in prompt:
            return (
                "Thought: Kiểm tra chính sách.\n"
                'Action: get_expense_policy({"category": "client_event", '
                '"amount": 12000000, "has_receipt": true, '
                '"department": "Marketing"})'
            )
        if "Action: check_department_budget" not in prompt:
            return (
                "Thought: Kiểm tra ngân sách.\n"
                'Action: check_department_budget({"department": "Marketing", '
                '"amount": 12000000})'
            )
        if "Action: get_approval_route" not in prompt:
            return (
                "Thought: Xác định tuyến duyệt.\n"
                'Action: get_approval_route({"amount": 12000000, '
                '"category": "client_event"})'
            )
        return "Thought: Đã đủ dữ liệu.\nFinal Answer: APPROVE - Đủ điều kiện."


class DashboardGuardrailTests(unittest.TestCase):
    def test_human_approval_normalizes_approve_to_escalate(self):
        result = run_debug_react(
            "Nhân viên E102 đề nghị 12000000 VND loại client_event.",
            HumanApprovalProvider(),
        )

        self.assertTrue(result["answer"].startswith("ESCALATE"))
        self.assertEqual(result["trace"][-1]["type"], "guardrail")
        self.assertEqual(
            result["tools_used"],
            [
                "get_employee_profile",
                "get_expense_policy",
                "check_department_budget",
                "get_approval_route",
            ],
        )


if __name__ == "__main__":
    unittest.main()
