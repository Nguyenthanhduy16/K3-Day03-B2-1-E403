"""Deterministic tools for the enterprise expense approval assistant."""

import json
import os
from typing import Any


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")


def _json_result(**payload: Any) -> str:
    """Serialize a tool result consistently for an agent observation."""
    return json.dumps(payload, ensure_ascii=False)


def _load_config(filename: str) -> dict[str, Any]:
    """Load one UTF-8 JSON configuration file."""
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _parse_amount(amount: Any) -> float:
    """Validate and normalize a positive expense amount."""
    if isinstance(amount, bool):
        raise ValueError("Số tiền phải là một số dương.")
    parsed = float(amount)
    if parsed <= 0:
        raise ValueError("Số tiền phải lớn hơn 0.")
    return parsed


def get_employee_profile(employee_id: str) -> str:
    """Return department and approval metadata for an employee ID."""
    normalized_id = str(employee_id).strip().upper()
    if not normalized_id:
        return _json_result(ok=False, error="Thiếu mã nhân viên.")

    profiles = _load_config("employee_profiles.json")
    profile = profiles.get(normalized_id)
    if profile is None:
        return _json_result(
            ok=False,
            error=f"Không tìm thấy nhân viên '{normalized_id}'.",
        )
    return _json_result(ok=True, employee_id=normalized_id, **profile)


def get_expense_policy(
    category: str,
    amount: float,
    has_receipt: bool,
    department: str = "",
) -> str:
    """Check a request against the demo policy for its expense category."""
    try:
        parsed_amount = _parse_amount(amount)
    except (TypeError, ValueError) as exc:
        return _json_result(ok=False, eligible=False, error=str(exc))

    normalized_category = str(category).strip().lower()
    policies = _load_config("expense_policies.json")
    policy = policies.get(normalized_category)
    if not isinstance(policy, dict):
        valid_categories = sorted(
            key for key, value in policies.items() if isinstance(value, dict)
        )
        return _json_result(
            ok=False,
            eligible=False,
            error=f"Loại chi phí '{category}' không tồn tại.",
            valid_categories=valid_categories,
        )

    reasons = []
    if parsed_amount > policy["per_request_limit"]:
        reasons.append("Số tiền vượt hạn mức mỗi yêu cầu.")
    if policy["receipt_required"] and not has_receipt:
        reasons.append("Thiếu hóa đơn bắt buộc.")
    if department and department not in policy["allowed_departments"]:
        reasons.append("Phòng ban không được phép dùng loại chi phí này.")

    return _json_result(
        ok=True,
        category=normalized_category,
        amount=parsed_amount,
        currency="VND",
        eligible=not reasons,
        reasons=reasons,
        policy=policy,
        source="config/expense_policies.json",
    )


def check_department_budget(department: str, amount: float) -> str:
    """Check whether a department has enough remaining demo budget."""
    try:
        parsed_amount = _parse_amount(amount)
    except (TypeError, ValueError) as exc:
        return _json_result(ok=False, sufficient=False, error=str(exc))

    normalized_department = str(department).strip()
    budgets = _load_config("department_budgets.json")
    budget = budgets.get(normalized_department)
    if budget is None:
        return _json_result(
            ok=False,
            sufficient=False,
            error=f"Không tìm thấy ngân sách phòng '{normalized_department}'.",
        )

    remaining = float(budget["remaining"])
    return _json_result(
        ok=True,
        department=normalized_department,
        requested=parsed_amount,
        remaining=remaining,
        sufficient=remaining >= parsed_amount,
        remaining_after=remaining - parsed_amount,
        currency=budget["currency"],
        source="config/department_budgets.json",
    )


def get_approval_route(amount: float, category: str) -> str:
    """Return the human approval chain for a positive expense amount."""
    try:
        parsed_amount = _parse_amount(amount)
    except (TypeError, ValueError) as exc:
        return _json_result(ok=False, error=str(exc))

    policies = _load_config("expense_policies.json")
    if category not in policies or not isinstance(policies[category], dict):
        return _json_result(
            ok=False,
            error=f"Không thể xác định tuyến duyệt cho loại '{category}'.",
        )

    for route in policies["approval_routes"]:
        maximum = route["max_amount"]
        if maximum is None or parsed_amount <= maximum:
            return _json_result(
                ok=True,
                amount=parsed_amount,
                category=category,
                approvers=route["approvers"],
                human_approval_required=True,
                source="config/expense_policies.json",
            )

    return _json_result(ok=False, error="Không xác định được tuyến phê duyệt.")


AVAILABLE_TOOLS = {
    "get_employee_profile": get_employee_profile,
    "get_expense_policy": get_expense_policy,
    "check_department_budget": check_department_budget,
    "get_approval_route": get_approval_route,
}
