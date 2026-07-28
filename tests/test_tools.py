"""Unit tests for deterministic expense tools."""

import json
import os
import sys
import unittest


SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, SRC_DIR)

from tools import (  # noqa: E402
    check_department_budget,
    get_approval_route,
    get_employee_profile,
    get_expense_policy,
)


class ExpenseToolTests(unittest.TestCase):
    def test_known_employee_returns_department(self):
        result = json.loads(get_employee_profile("e102"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["department"], "Marketing")

    def test_unknown_employee_returns_safe_error(self):
        result = json.loads(get_employee_profile("E999"))
        self.assertFalse(result["ok"])
        self.assertIn("Không tìm thấy", result["error"])

    def test_meal_with_receipt_is_eligible(self):
        result = json.loads(get_expense_policy("meal", 800000, True))
        self.assertTrue(result["eligible"])
        self.assertEqual(result["policy"]["per_request_limit"], 1000000)

    def test_missing_receipt_is_ineligible(self):
        result = json.loads(get_expense_policy("meal", 500000, False))
        self.assertFalse(result["eligible"])
        self.assertIn("Thiếu hóa đơn bắt buộc.", result["reasons"])

    def test_negative_amount_returns_safe_error(self):
        result = json.loads(get_expense_policy("meal", -1, True))
        self.assertFalse(result["ok"])
        self.assertFalse(result["eligible"])

    def test_insufficient_budget_is_reported(self):
        result = json.loads(check_department_budget("Sales", 6000000))
        self.assertTrue(result["ok"])
        self.assertFalse(result["sufficient"])

    def test_high_value_route_requires_cfo(self):
        result = json.loads(get_approval_route(12000000, "client_event"))
        self.assertEqual(result["approvers"], ["Manager", "Finance", "CFO"])
        self.assertTrue(result["human_approval_required"])


if __name__ == "__main__":
    unittest.main()
