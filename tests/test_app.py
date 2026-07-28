"""Integration tests for parsing, dispatch and ReAct guardrails."""

import os
import sys
import unittest


SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, SRC_DIR)

from app import (  # noqa: E402
    execute_tool,
    load_test_cases,
    parse_agent_response,
    run_react_agent,
)
from providers import MockProvider  # noqa: E402


class RepeatingProvider:
    def generate(self, prompt, system_prompt=""):
        return (
            "Thought: Thử lại cùng hành động.\n"
            'Action: get_employee_profile({"employee_id": "E102"})'
        )


class AppTests(unittest.TestCase):
    def test_parse_json_action(self):
        parsed = parse_agent_response(
            "Thought: Kiểm tra hồ sơ.\n"
            'Action: get_employee_profile({"employee_id": "E102"})'
        )
        self.assertEqual(parsed["type"], "action")
        self.assertEqual(parsed["arguments"]["employee_id"], "E102")

    def test_malformed_action_is_invalid(self):
        parsed = parse_agent_response(
            "Thought: Thiếu ngoặc.\n"
            'Action: get_employee_profile({"employee_id": "E102"}'
        )
        self.assertEqual(parsed["type"], "invalid")

    def test_unknown_tool_returns_recovery_observation(self):
        observation = execute_tool("delete_budget", {})
        self.assertIn("không tồn tại", observation)
        self.assertIn("available_tools", observation)

    def test_all_acceptance_tool_paths(self):
        provider = MockProvider()
        for test_case in load_test_cases():
            with self.subTest(test_id=test_case["id"]):
                result = run_react_agent(
                    test_case["question"],
                    provider,
                    verbose=False,
                )
                self.assertEqual(
                    result["tools_used"],
                    test_case["expected_tools"],
                )
                self.assertEqual(result["status"], "completed")

    def test_repeated_action_triggers_guardrail(self):
        result = run_react_agent(
            "Kiểm tra một yêu cầu bất kỳ.",
            RepeatingProvider(),
            verbose=False,
        )
        self.assertEqual(result["status"], "guardrail")
        self.assertIn("lặp lại", result["answer"])


if __name__ == "__main__":
    unittest.main()
