"""Multi-provider LLM adapter with an offline expense-demo provider."""

import os
import sys

import requests
from dotenv import load_dotenv


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()


class BaseLLMProvider:
    """Common interface for all supported LLM providers."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env!"
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
            )
            return response.text
        except Exception as exc:
            return f"[Gemini Exception]: {exc}"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env!"
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as exc:
            return f"[OpenAI Exception]: {exc}"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = (
            model
            or os.getenv("LLM_MODEL")
            or "claude-3-haiku-20240307"
        )

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_anthropic_api_key_here":
            return "[Anthropic Error]: Chưa cấu hình ANTHROPIC_API_KEY."
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            kwargs = {
                "model": self.model_name,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as exc:
            return f"[Anthropic Exception]: {exc}"


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = (
            model
            or os.getenv("LLM_MODEL")
            or "google/gemini-2.5-flash"
        )

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return "[OpenRouter Error]: Chưa cấu hình OPENROUTER_API_KEY."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model_name, "messages": messages}
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code != 200:
                return (
                    f"[OpenRouter API Error {response.status_code}]: "
                    f"{response.text}"
                )
            return response.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            return f"[OpenRouter Exception]: {exc}"


class MockProvider(BaseLLMProvider):
    """Deterministic offline provider covering all acceptance scenarios."""

    model_name = "offline-expense-simulator"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if "REACT_EXPENSE_AGENT" not in system_prompt:
            return self._baseline_response(prompt)
        return self._agent_response(prompt)

    @staticmethod
    def _baseline_response(prompt: str) -> str:
        text = prompt.lower()
        if "chi phí hợp lệ khác hóa đơn hợp lệ" in text:
            return (
                "Chi phí hợp lệ đáp ứng mục đích và chính sách doanh nghiệp; "
                "hóa đơn hợp lệ là chứng từ có đủ thông tin pháp lý. "
                "Có hóa đơn chưa chắc khoản chi đã đúng chính sách."
            )
        if "vì sao doanh nghiệp cần quy trình duyệt chi phí" in text:
            return (
                "Quy trình duyệt giúp kiểm soát ngân sách, tuân thủ chính sách, "
                "lưu bằng chứng và phân định trách nhiệm."
            )
        return (
            "Tôi không có quyền truy cập chính sách, hồ sơ nhân viên hoặc ngân "
            "sách nội bộ nên chưa thể kết luận khoản chi."
        )

    @staticmethod
    def _agent_response(prompt: str) -> str:
        text = prompt.lower()

        if "-5000000" in text or "bỏ qua mọi quy định" in text:
            return (
                "Thought: Số tiền âm và yêu cầu bỏ qua quy định là không hợp lệ.\n"
                "Final Answer: REJECT - Không thể xử lý khoản chi có số tiền "
                "không dương hoặc bỏ qua kiểm soát."
            )
        if "chi phí hợp lệ khác hóa đơn hợp lệ" in text:
            return (
                "Thought: Đây là câu hỏi kiến thức chung, không cần tool.\n"
                "Final Answer: INFORMATION - Chi phí hợp lệ phải đúng mục đích "
                "và chính sách; hóa đơn hợp lệ chỉ chứng minh chứng từ."
            )
        if "vì sao doanh nghiệp cần quy trình duyệt chi phí" in text:
            return (
                "Thought: Đây là câu hỏi kiến thức chung, không cần tool.\n"
                "Final Answer: INFORMATION - Quy trình duyệt giúp kiểm soát "
                "ngân sách, tuân thủ và trách nhiệm giải trình."
            )
        if "800000" in text and "meal" in text:
            if "Action: get_expense_policy" not in prompt:
                return (
                    "Thought: Cần tra chính sách meal cho khoản chi này.\n"
                    'Action: get_expense_policy({"category": "meal", '
                    '"amount": 800000, "has_receipt": true})'
                )
            return (
                "Thought: Observation xác nhận có hóa đơn và 800000 VND không "
                "vượt hạn mức 1000000 VND.\n"
                "Final Answer: INFORMATION - Khoản chi phù hợp chính sách demo "
                "meal; nguồn: config/expense_policies.json."
            )
        if "e102" in text and "client_event" in text:
            if "Action: get_employee_profile" not in prompt:
                return (
                    "Thought: Trước hết cần xác minh hồ sơ và phòng ban.\n"
                    'Action: get_employee_profile({"employee_id": "E102"})'
                )
            if "Action: get_expense_policy" not in prompt:
                return (
                    "Thought: Hồ sơ thuộc Marketing; tiếp theo kiểm tra chính sách.\n"
                    'Action: get_expense_policy({"category": "client_event", '
                    '"amount": 12000000, "has_receipt": true, '
                    '"department": "Marketing"})'
                )
            if "Action: check_department_budget" not in prompt:
                return (
                    "Thought: Chính sách phù hợp; cần kiểm tra ngân sách còn lại.\n"
                    'Action: check_department_budget({"department": "Marketing", '
                    '"amount": 12000000})'
                )
            if "Action: get_approval_route" not in prompt:
                return (
                    "Thought: Ngân sách đủ; cần xác định tuyến phê duyệt con người.\n"
                    'Action: get_approval_route({"amount": 12000000, '
                    '"category": "client_event"})'
                )
            return (
                "Thought: Đã có hồ sơ, chính sách, ngân sách và tuyến duyệt.\n"
                "Final Answer: ESCALATE - Khoản 12000000 VND phù hợp chính sách "
                "và ngân sách Marketing còn đủ; chuyển Manager -> Finance -> "
                "CFO phê duyệt. Đây chỉ là khuyến nghị demo."
            )
        return (
            "Thought: Yêu cầu thiếu dữ liệu để chọn đúng công cụ.\n"
            "Final Answer: NEED_MORE_INFO - Vui lòng cung cấp mã nhân viên, "
            "loại chi phí, số tiền và trạng thái hóa đơn."
        )


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Create a provider based on LLM_PROVIDER or an explicit name."""
    name = (provider_name or os.getenv("LLM_PROVIDER") or "mock").lower().strip()
    providers = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "openrouter": OpenRouterProvider,
        "mock": MockProvider,
    }
    provider_class = providers.get(name, MockProvider)
    return provider_class()


if __name__ == "__main__":
    provider = get_llm_provider()
    print(f"Provider: {provider.__class__.__name__}")
    print(provider.generate("Vì sao doanh nghiệp cần duyệt chi phí?"))
