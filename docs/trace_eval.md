# Báo cáo giám sát: Trợ lý Duyệt Chi phí

> Dữ liệu và quyết định trong báo cáo chỉ phục vụ bài lab, không phải chính
> sách hay phê duyệt thật của doanh nghiệp.

## 1. Agentic Fit

| Tiêu chí | Điểm | Lý do |
|---|:---:|---|
| Multi-step Reasoning | 5/5 | Phải nối hồ sơ, chính sách, ngân sách và tuyến duyệt. |
| Tool Interaction | 5/5 | Kết luận cần bằng chứng từ nhiều nguồn nội bộ giả lập. |
| Dynamic Decision | 5/5 | Observation trước quyết định Action tiếp theo. |
| Long Horizon | 4/5 | Luồng đầy đủ cần bốn Action và một Final Answer. |
| **Tổng** | **19/20** | **Rất phù hợp với ReAct Agent.** |

## 2. Baseline và ReAct — Test #3

**Câu hỏi:** Khoản meal 800.000 VND có hóa đơn có phù hợp chính sách không?

- **Baseline:** Không có quyền truy cập chính sách nội bộ nên không kết luận.
  Phản hồi an toàn nhưng chưa giải quyết yêu cầu.
- **ReAct:** gọi `get_expense_policy`, nhận hạn mức 1.000.000 VND và yêu cầu
  hóa đơn, sau đó kết luận khoản chi phù hợp chính sách demo.

## 3. Trace thành công — Test #4

```text
Question: E102/Marketing đề nghị 12.000.000 VND cho client_event, có hóa đơn.

Thought 1: Cần xác minh hồ sơ và phòng ban.
Action 1: get_employee_profile({"employee_id": "E102"})
Observation 1: E102 thuộc Marketing, manager MKT-MGR.

Thought 2: Cần kiểm tra chính sách client_event.
Action 2: get_expense_policy({"category": "client_event",
          "amount": 12000000, "has_receipt": true,
          "department": "Marketing"})
Observation 2: eligible=true, hạn mức 20.000.000 VND.

Thought 3: Cần kiểm tra ngân sách Marketing.
Action 3: check_department_budget({"department": "Marketing",
          "amount": 12000000})
Observation 3: sufficient=true, còn lại sau chi là 18.000.000 VND.

Thought 4: Cần xác định tuyến phê duyệt con người.
Action 4: get_approval_route({"amount": 12000000,
          "category": "client_event"})
Observation 4: Manager -> Finance -> CFO.

Final Answer: ESCALATE - Đủ điều kiện demo; chuyển Manager -> Finance -> CFO.
```

## 4. Failed Trace và Agent V2

**Lỗi tái hiện:** một provider liên tục trả lại cùng
`get_employee_profile({"employee_id": "E102"})` dù đã nhận Observation.

**RCA:** LLM bỏ qua trạng thái đã thực thi và không tự nhận biết vòng lặp.

**Khắc phục V2:** `src/app.py` tạo fingerprint từ tên tool và JSON arguments,
đếm Action trùng, sau đó trả `NEED_MORE_INFO` khi vượt
`MAX_REPEATED_ACTIONS`. Unknown tool, JSON sai và thiếu tham số cũng được đưa
về Observation thay vì làm ứng dụng crash.

## 5. Kết quả nghiệm thu offline

| Test | Hybrid path | Tool path | Kết quả |
|---:|---|---|:---:|
| 1 | Chatbot | Không gọi tool | PASS |
| 2 | Chatbot | Không gọi tool | PASS |
| 3 | ReAct | `get_expense_policy` | PASS |
| 4 | ReAct | Profile → Policy → Budget → Route | PASS |
| 5 | ReAct guardrail | Không gọi tool; `REJECT` input âm/injection | PASS |

Kết quả chạy với `MockProvider`: **5/5 acceptance tool paths PASS**. Kết quả
với provider thật có thể khác và phải được lưu lại khi nhóm chạy nghiệm thu.

## 6. Bảo mật và giới hạn

- Tool đều read-only; ứng dụng không giải ngân hay cập nhật ngân sách.
- Chính sách, hồ sơ và ngân sách là dữ liệu giả lập trong `config/`.
- `.env` và API keys không được commit.
- Mọi `APPROVE` hoặc `ESCALATE` chỉ là khuyến nghị, cần con người phê duyệt.
