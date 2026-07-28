"""Deterministic Level 1 expense rules used before LLM-based processing."""

from __future__ import annotations

import json
import re
from typing import Any, Callable


ToolExecutor = Callable[[str, dict[str, Any]], str]

EMPLOYEE_PATTERN = re.compile(r"\bE\d{3,}\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(
    r"(?<![A-Za-z])(-?\d[\d.,\s]{2,})\s*(?:VND|VNĐ|đồng|đ)\b",
    re.IGNORECASE,
)
CATEGORY_KEYWORDS = {
    "client_event": ("client_event", "sự kiện khách hàng", "tiếp khách hàng"),
    "office_supplies": ("office_supplies", "văn phòng phẩm"),
    "travel": ("travel", "công tác", "đi lại"),
    "meal": ("meal", "ăn uống", "ăn tiếp khách"),
}


def _extract_amount(text: str) -> float | None:
    match = AMOUNT_PATTERN.search(text)
    if not match:
        return None
    normalized = re.sub(r"[\s.,]", "", match.group(1))
    try:
        return float(normalized)
    except ValueError:
        return None


def _extract_category(text: str) -> str | None:
    folded = text.casefold()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in folded for keyword in keywords):
            return category
    return None


def _extract_receipt(text: str) -> bool | None:
    folded = text.casefold()
    negatives = ("không có hóa đơn", "không hóa đơn", "without receipt")
    positives = ("có hóa đơn", "kèm hóa đơn", "with receipt")
    if any(phrase in folded for phrase in negatives):
        return False
    if any(phrase in folded for phrase in positives):
        return True
    return None


def _result(
    status: str,
    answer: str,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": status,
        "answer": answer,
        "tools_used": [item["tool"] for item in trace if item.get("tool")],
        "trace": trace,
    }


def _terminal_step(
    trace: list[dict[str, Any]],
    step_type: str,
    decision: str,
    answer: str,
) -> None:
    trace.append(
        {
            "step": len(trace) + 1,
            "type": step_type,
            "model_response": f"Thought: Level 1 rule — {decision}",
            "answer": answer,
            "latency_ms": 0,
        }
    )


def run_rule_based(question: str, execute_tool: ToolExecutor) -> dict[str, Any]:
    """Evaluate one request with deterministic extraction, rules, and tools."""
    trace: list[dict[str, Any]] = []
    text = question.strip()
    folded = text.casefold()
    amount = _extract_amount(text)
    category = _extract_category(text)
    receipt = _extract_receipt(text)
    employee_match = EMPLOYEE_PATTERN.search(text)
    employee_id = employee_match.group(0).upper() if employee_match else None
    approval_intent = any(
        phrase in folded for phrase in ("duyệt", "phê duyệt", "approve", "approval")
    )

    if amount is not None and amount <= 0:
        answer = "REJECT - Level 1 từ chối khoản chi có số tiền không dương."
        _terminal_step(trace, "guardrail", "amount <= 0", answer)
        return _result("completed", answer, trace)

    missing = []
    if amount is None:
        missing.append("số tiền kèm đơn vị VND")
    if category is None:
        missing.append("loại chi phí")
    if receipt is None:
        missing.append("trạng thái hóa đơn")
    if missing:
        answer = "NEED_MORE_INFO - Vui lòng bổ sung " + ", ".join(missing) + "."
        _terminal_step(trace, "guardrail", f"thiếu trường bắt buộc: {', '.join(missing)}", answer)
        return _result("completed", answer, trace)

    department = None

    def call(tool: str, arguments: dict[str, Any], decision: str) -> dict[str, Any]:
        observation = execute_tool(tool, arguments)
        trace.append(
            {
                "step": len(trace) + 1,
                "type": "action",
                "model_response": (
                    f"Thought: Level 1 rule — {decision}\n"
                    f"Action: {tool}({json.dumps(arguments, ensure_ascii=False)})"
                ),
                "tool": tool,
                "arguments": arguments,
                "observation": observation,
                "latency_ms": 0,
            }
        )
        try:
            return json.loads(observation)
        except json.JSONDecodeError:
            return {"ok": False, "error": "Tool trả dữ liệu không hợp lệ."}

    if employee_id:
        profile = call(
            "get_employee_profile",
            {"employee_id": employee_id},
            "có mã nhân viên nên xác minh hồ sơ trước",
        )
        if not profile.get("ok"):
            answer = f"NEED_MORE_INFO - {profile.get('error', 'Không xác minh được nhân viên.')}"
            _terminal_step(trace, "guardrail", "không xác minh được hồ sơ", answer)
            return _result("completed", answer, trace)
        department = profile.get("department")

    policy_arguments: dict[str, Any] = {
        "category": category,
        "amount": amount,
        "has_receipt": receipt,
    }
    if department:
        policy_arguments["department"] = department
    policy = call(
        "get_expense_policy",
        policy_arguments,
        "đủ dữ liệu tối thiểu nên kiểm tra hạn mức và hóa đơn",
    )
    if not policy.get("ok") or not policy.get("eligible"):
        reasons = policy.get("reasons") or [policy.get("error", "Không đạt chính sách.")]
        answer = "REJECT - " + " ".join(str(reason) for reason in reasons)
        _terminal_step(trace, "final", "policy.eligible != true", answer)
        return _result("completed", answer, trace)

    if not approval_intent:
        answer = (
            "INFORMATION - Khoản chi phù hợp chính sách Level 1; "
            "chưa thực hiện kiểm tra ngân sách hoặc tuyến phê duyệt."
        )
        _terminal_step(trace, "final", "chỉ yêu cầu kiểm tra chính sách", answer)
        return _result("completed", answer, trace)

    if not department:
        answer = (
            "NEED_MORE_INFO - Cần mã nhân viên để xác định phòng ban, "
            "kiểm tra ngân sách và tuyến phê duyệt."
        )
        _terminal_step(trace, "guardrail", "thiếu phòng ban cho yêu cầu phê duyệt", answer)
        return _result("completed", answer, trace)

    budget = call(
        "check_department_budget",
        {"department": department, "amount": amount},
        "yêu cầu phê duyệt nên phải kiểm tra ngân sách phòng ban",
    )
    if not budget.get("ok") or not budget.get("sufficient"):
        answer = "REJECT - Ngân sách phòng ban không đủ hoặc không thể xác minh."
        _terminal_step(trace, "final", "budget.sufficient != true", answer)
        return _result("completed", answer, trace)

    route = call(
        "get_approval_route",
        {"amount": amount, "category": category},
        "policy và ngân sách đạt nên xác định người phê duyệt",
    )
    if not route.get("ok"):
        answer = f"NEED_MORE_INFO - {route.get('error', 'Không xác định được tuyến duyệt.')}"
        _terminal_step(trace, "guardrail", "không xác định được tuyến phê duyệt", answer)
        return _result("completed", answer, trace)

    approvers = " → ".join(route.get("approvers", []))
    answer = (
        "ESCALATE - Các rule tự động đã đạt; chuyển "
        f"{approvers} xác nhận trước khi chi."
    )
    _terminal_step(trace, "final", "human_approval_required = true", answer)
    return _result("completed", answer, trace)
