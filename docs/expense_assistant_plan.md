# Kế hoạch triển khai Trợ lý Duyệt Chi phí

## Phạm vi MVP

Ứng dụng dùng dữ liệu giả lập để kiểm tra hồ sơ nhân viên, chính sách, ngân
sách và tuyến phê duyệt. Agent chỉ đưa ra `APPROVE`, `REJECT`, `ESCALATE`,
`NEED_MORE_INFO` hoặc `INFORMATION`; không thay đổi ngân sách hay phê duyệt
giao dịch thật.

## Phân công theo file

| Vai trò | File chính | Kết quả cần bàn giao |
|---|---|---|
| Product Architect | `config/*.json` | Dữ liệu demo và 5 acceptance cases |
| Tool Engineer | `src/tools.py` | 4 tool read-only, lỗi không làm crash |
| Prompt Engineer | `src/prompts.py` | Baseline, ReAct format và guardrails |
| Core Integrator | `src/app.py` | Parser, dispatcher, loop và hybrid route |
| Observability | `docs/trace_eval.md` | Matrix, trace, RCA và kết quả đánh giá |

## Bốn mốc nghiệm thu

1. **Agentic Fit:** thống nhất phạm vi và chấm 19/20.
2. **Baseline & Tools:** tool unit tests pass; baseline không dùng dữ liệu nội bộ.
3. **ReAct V2:** Action JSON được parse, Observation quay lại prompt, loop dừng
   bởi Final Answer hoặc guardrail.
4. **Evaluation:** 5/5 tool paths pass ở MockProvider; có failed trace, hybrid
   flowchart và kiểm tra bảo mật.

## Chạy nghiệm thu

```powershell
$env:LLM_PROVIDER = "mock"
python src/app.py
python -m unittest discover -s tests -v
python -m compileall src
```
