"""Core application for the enterprise expense approval lab."""

import inspect
import json
import os
import re
import sys
from typing import Any

from dotenv import load_dotenv


SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SRC_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from prompts import (  # noqa: E402
    CHATBOT_BASELINE_PROMPT,
    MAX_ITERATIONS,
    MAX_REPEATED_ACTIONS,
    REACT_SYSTEM_PROMPT,
)
from providers import get_llm_provider  # noqa: E402
from tools import AVAILABLE_TOOLS  # noqa: E402


load_dotenv()

ACTION_PATTERN = re.compile(
    r"^Action:\s*([A-Za-z_]\w*)\((\{[^\r\n]*\})\)\s*$",
    re.MULTILINE,
)
FINAL_PATTERN = re.compile(r"Final Answer:\s*(.+)", re.DOTALL)


def load_test_cases() -> list[dict[str, Any]]:
    """Load the acceptance scenarios from config/test_cases.json."""
    path = os.path.join(BASE_DIR, "config", "test_cases.json")
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def run_baseline_chatbot(
    user_query: str,
    provider: Any,
    verbose: bool = True,
) -> str:
    """Run exactly one LLM call without exposing any tools."""
    response = provider.generate(
        user_query,
        system_prompt=CHATBOT_BASELINE_PROMPT,
    )
    if verbose:
        print(f"Baseline: {response}")
    return response


def parse_agent_response(response: str) -> dict[str, Any]:
    """Parse one Final Answer or one JSON-formatted Action."""
    final_match = FINAL_PATTERN.search(response)
    if final_match:
        return {
            "type": "final",
            "answer": final_match.group(1).strip(),
        }

    action_match = ACTION_PATTERN.search(response)
    if not action_match:
        return {
            "type": "invalid",
            "error": (
                "Phản hồi không có Final Answer hoặc Action đúng định dạng."
            ),
        }

    tool_name, raw_arguments = action_match.groups()
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        return {
            "type": "invalid",
            "error": f"Action chứa JSON không hợp lệ: {exc.msg}.",
        }
    if not isinstance(arguments, dict):
        return {
            "type": "invalid",
            "error": "Tham số Action phải là một JSON object.",
        }
    return {
        "type": "action",
        "tool": tool_name,
        "arguments": arguments,
    }


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Validate and execute one registered read-only tool."""
    tool = AVAILABLE_TOOLS.get(tool_name)
    if tool is None:
        return json.dumps(
            {
                "ok": False,
                "error": f"Tool '{tool_name}' không tồn tại.",
                "available_tools": sorted(AVAILABLE_TOOLS),
            },
            ensure_ascii=False,
        )

    try:
        inspect.signature(tool).bind(**arguments)
        return tool(**arguments)
    except TypeError as exc:
        return json.dumps(
            {
                "ok": False,
                "error": f"Tham số tool không hợp lệ: {exc}",
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "error": f"Tool thất bại an toàn: {exc}",
            },
            ensure_ascii=False,
        )


def _fallback(reason: str, trace: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "guardrail",
        "answer": f"NEED_MORE_INFO - {reason}",
        "tools_used": [
            item["tool"] for item in trace if item.get("tool") is not None
        ],
        "trace": trace,
    }


def run_react_agent(
    user_query: str,
    provider: Any,
    verbose: bool = True,
) -> dict[str, Any]:
    """Run the Thought -> Action -> Observation loop with guardrails."""
    history = f"Question: {user_query}"
    trace: list[dict[str, Any]] = []
    action_counts: dict[str, int] = {}

    for step in range(1, MAX_ITERATIONS + 1):
        response = provider.generate(
            history,
            system_prompt=REACT_SYSTEM_PROMPT,
        )
        parsed = parse_agent_response(response)

        if verbose:
            print(f"\n--- ReAct step {step}/{MAX_ITERATIONS} ---")
            print(response)

        if parsed["type"] == "final":
            answer = parsed["answer"]
            if (
                answer.startswith(("APPROVE", "ESCALATE"))
                and not trace
            ):
                observation = json.dumps(
                    {
                        "ok": False,
                        "error": (
                            "Kết luận cần bằng chứng từ tool trước khi trả lời."
                        ),
                    },
                    ensure_ascii=False,
                )
                history += f"\n{response}\nObservation: {observation}"
                continue
            return {
                "status": "completed",
                "answer": answer,
                "tools_used": [
                    item["tool"]
                    for item in trace
                    if item.get("tool") is not None
                ],
                "trace": trace,
            }

        if parsed["type"] == "invalid":
            observation = json.dumps(
                {"ok": False, "error": parsed["error"]},
                ensure_ascii=False,
            )
            trace.append(
                {
                    "step": step,
                    "tool": None,
                    "arguments": None,
                    "observation": observation,
                }
            )
            history += f"\n{response}\nObservation: {observation}"
            if verbose:
                print(f"Observation: {observation}")
            continue

        fingerprint = json.dumps(
            [parsed["tool"], parsed["arguments"]],
            ensure_ascii=False,
            sort_keys=True,
        )
        action_counts[fingerprint] = action_counts.get(fingerprint, 0) + 1
        if action_counts[fingerprint] > MAX_REPEATED_ACTIONS:
            return _fallback(
                "Agent lặp lại cùng một Action quá số lần cho phép.",
                trace,
            )

        observation = execute_tool(
            parsed["tool"],
            parsed["arguments"],
        )
        trace.append(
            {
                "step": step,
                "tool": parsed["tool"],
                "arguments": parsed["arguments"],
                "observation": observation,
            }
        )
        history += f"\n{response}\nObservation: {observation}"
        if verbose:
            print(f"Observation: {observation}")

    return _fallback(
        f"Đã đạt MAX_ITERATIONS={MAX_ITERATIONS}; dừng an toàn.",
        trace,
    )


def choose_hybrid_route(test_case: dict[str, Any]) -> str:
    """Choose the economical route described by the lab flowchart."""
    return "REACT_AGENT" if test_case["requires_tools"] else "CHATBOT"


def evaluate_tool_path(
    expected_tools: list[str],
    actual_tools: list[str],
) -> bool:
    """Check exact tool order for one deterministic acceptance scenario."""
    return expected_tools == actual_tools


def main() -> None:
    """Run all scenarios through the selected hybrid route."""
    print("=" * 68)
    print("TRO LY DUYET CHI PHI DOANH NGHIEP - CHATBOT VS REACT")
    print("=" * 68)

    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "default")
    print(f"Provider: {provider.__class__.__name__} ({model_name})")

    test_cases = load_test_cases()
    passed_paths = 0
    for test_case in test_cases:
        print(
            f"\nTEST #{test_case['id']} - {test_case['category']}"
            f"\nHybrid route: {choose_hybrid_route(test_case)}"
            f"\nQuestion: {test_case['question']}"
        )
        if test_case["requires_tools"]:
            baseline = run_baseline_chatbot(test_case["question"], provider)
            result = run_react_agent(test_case["question"], provider)
        else:
            baseline = run_baseline_chatbot(test_case["question"], provider)
            result = {
                "status": "completed",
                "answer": baseline,
                "tools_used": [],
                "trace": [],
            }
        path_passed = evaluate_tool_path(
            test_case["expected_tools"],
            result["tools_used"],
        )
        passed_paths += int(path_passed)
        print(f"Final: {result['answer']}")
        print(
            f"Tool path: {result['tools_used']} "
            f"({'PASS' if path_passed else 'FAIL'})"
        )

    print(f"\nAcceptance tool paths: {passed_paths}/{len(test_cases)} PASS")


if __name__ == "__main__":
    main()






