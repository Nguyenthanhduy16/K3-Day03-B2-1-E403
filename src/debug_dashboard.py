"""Polished interactive dashboard for the expense chatbot and ReAct agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from dotenv import load_dotenv


SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from app import execute_tool, parse_agent_response, run_baseline_chatbot  # noqa: E402
from prompts import MAX_ITERATIONS, MAX_REPEATED_ACTIONS, REACT_SYSTEM_PROMPT  # noqa: E402
from providers import get_llm_provider  # noqa: E402
from rule_based import run_rule_based  # noqa: E402
from tools import AVAILABLE_TOOLS  # noqa: E402


load_dotenv()


HTML = r"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Expense Agent · Demo Console</title>
  <style>
    :root{color-scheme:dark;--bg:#07111f;--panel:#0d1a2b;--panel2:#122238;--line:#243a55;--text:#eef6ff;--muted:#8fa6bf;--cyan:#36d6d0;--blue:#5b8cff;--green:#4ade80;--amber:#fbbf24;--red:#fb7185;--purple:#a78bfa}
    *{box-sizing:border-box}body{margin:0;min-height:100vh;color:var(--text);background:radial-gradient(circle at 15% 0%,rgba(54,214,208,.12),transparent 32%),radial-gradient(circle at 90% 12%,rgba(91,140,255,.14),transparent 30%),var(--bg);font:14px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
    button,textarea,select{font:inherit}button{cursor:pointer}header{min-height:72px;padding:14px 24px;border-bottom:1px solid rgba(255,255,255,.08);background:rgba(7,17,31,.82);backdrop-filter:blur(16px);display:flex;align-items:center;justify-content:space-between;gap:18px;position:sticky;top:0;z-index:10}
    .brand{display:flex;align-items:center;gap:12px}.logo{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(135deg,var(--cyan),var(--blue));color:#06101c;font-size:22px;box-shadow:0 8px 28px rgba(54,214,208,.25)}
    h1{margin:0;font-size:18px;letter-spacing:-.02em}.sub,.help{color:var(--muted);font-size:12px}.connection{display:flex;align-items:center;gap:9px;flex-wrap:wrap;justify-content:flex-end}.badge{display:inline-flex;align-items:center;gap:7px;padding:6px 10px;border:1px solid var(--line);border-radius:999px;background:rgba(13,26,43,.85);color:var(--muted);font-size:12px;white-space:nowrap}.dot{width:7px;height:7px;border-radius:50%;background:var(--amber)}.dot.live{background:var(--green);box-shadow:0 0 0 4px rgba(74,222,128,.12)}
    .layout{width:min(1540px,100%);margin:0 auto;padding:20px;display:grid;grid-template-columns:minmax(300px,380px) minmax(0,1fr);gap:18px}.card{border:1px solid var(--line);border-radius:16px;background:linear-gradient(160deg,rgba(18,34,56,.94),rgba(10,22,37,.96));box-shadow:0 18px 50px rgba(0,0,0,.25);overflow:hidden;min-width:0}.controls{padding:18px;align-self:start;position:sticky;top:92px}.title{margin:0 0 4px;font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--cyan)}.help{margin:0 0 15px}.level-map{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:12px 0 16px}.level-card{min-height:72px;text-align:left;padding:9px 10px;border:1px solid var(--line);border-radius:11px;color:var(--muted);background:rgba(7,17,31,.5);transition:.2s}.level-card b,.level-card span,.level-card small{display:block}.level-card b{color:var(--cyan);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.level-card span{color:var(--text);font-weight:750;margin-top:2px}.level-card small{font-size:10px;margin-top:1px}.level-card:hover,.level-card.active{border-color:var(--cyan);background:rgba(54,214,208,.08);box-shadow:inset 0 0 18px rgba(54,214,208,.05)}
    label{display:block;margin:14px 0 7px;font-weight:700}select,textarea{width:100%;color:var(--text);border:1px solid var(--line);border-radius:11px;background:rgba(7,17,31,.75);outline:none;transition:.2s}select{padding:10px 12px}textarea{min-height:155px;padding:12px;resize:vertical}select:focus,textarea:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(54,214,208,.1)}
    .primary{width:100%;border:0;border-radius:11px;margin-top:12px;padding:11px 14px;color:#06101c;font-weight:800;background:linear-gradient(90deg,var(--cyan),#73e7c3);box-shadow:0 10px 24px rgba(54,214,208,.16)}button:disabled{cursor:wait;opacity:.62}.samples{display:grid;gap:8px;margin-top:8px}.sample{text-align:left;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px 10px;background:rgba(7,17,31,.55)}.sample:hover{border-color:#45617f;background:var(--panel2)}.sample span{display:block;color:var(--muted);font-size:11px}
    .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.chip{padding:4px 7px;border-radius:7px;background:rgba(91,140,255,.09);border:1px solid rgba(91,140,255,.28);color:#b8ccff;font:11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}.workspace{display:grid;gap:16px;align-content:start}.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))}.metric{padding:14px 16px;border-right:1px solid var(--line)}.metric:last-child{border-right:0}.metric span{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.07em}.metric strong{display:block;margin-top:5px;font-size:18px;overflow-wrap:anywhere}.good{color:var(--green)}.warn{color:var(--amber)}
    .pipeline{padding:16px 18px;border-top:1px solid var(--line);display:flex;align-items:center;overflow-x:auto}.node{min-width:112px;padding:8px 10px;border:1px solid var(--line);border-radius:10px;background:rgba(7,17,31,.55);text-align:center;color:var(--muted);font-size:12px}.node.active{color:var(--text);border-color:var(--cyan);box-shadow:inset 0 0 20px rgba(54,214,208,.08)}.arrow{color:#4c6480;padding:0 8px}
    .head{padding:16px 18px;display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid var(--line)}.head h2{margin:0;font-size:15px}.outcome{padding:5px 10px;border-radius:999px;font-size:12px;font-weight:800;color:var(--muted);border:1px solid var(--line)}.outcome.approve,.outcome.information{color:var(--green);border-color:rgba(74,222,128,.36);background:rgba(74,222,128,.08)}.outcome.escalate,.outcome.need_more_info{color:var(--amber);border-color:rgba(251,191,36,.36);background:rgba(251,191,36,.08)}.outcome.reject,.outcome.error{color:var(--red);border-color:rgba(251,113,133,.36);background:rgba(251,113,133,.08)}
    .answer{padding:18px;white-space:pre-wrap;min-height:112px;font-size:15px}.evidence{padding:0 18px 18px;display:flex;flex-wrap:wrap;gap:8px}.secondary{border:1px solid var(--line);border-radius:8px;padding:7px 10px;color:var(--muted);background:var(--panel);font-size:12px}.secondary:hover{color:var(--text)}.trace{padding:8px 18px 18px}.empty{color:var(--muted);padding:26px 4px;text-align:center}
    .step{display:grid;grid-template-columns:38px minmax(0,1fr);gap:11px;padding-top:14px}.index{width:32px;height:32px;border:1px solid var(--line);border-radius:50%;display:grid;place-items:center;background:var(--panel2);color:var(--cyan);font-weight:800}.stepbox{border:1px solid var(--line);border-radius:12px;overflow:hidden}.stepbar{padding:10px 12px;display:flex;justify-content:space-between;gap:10px;background:rgba(7,17,31,.5)}.kind{font-weight:800}.latency{color:var(--muted);font-size:11px}.decision{padding:11px 12px;color:#cfe0f2}.call{margin:0 12px 12px;border-left:3px solid var(--blue);background:rgba(91,140,255,.07);border-radius:7px;padding:10px}.call.obs{border-left-color:var(--purple);background:rgba(167,139,250,.07)}.call-label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.09em;margin-bottom:5px}pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;color:#dce9f8;font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}details{margin:0 12px 12px;color:var(--muted);font-size:12px}details pre{margin-top:8px;border:1px solid var(--line);border-radius:8px;padding:9px;background:#07111f}.errorbox{border-color:rgba(251,113,133,.5);color:#fecdd3}
    .spinner{display:inline-block;width:13px;height:13px;border:2px solid rgba(6,16,28,.25);border-top-color:#06101c;border-radius:50%;animation:spin .8s linear infinite;vertical-align:-2px;margin-right:7px}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:1050px){.layout{grid-template-columns:1fr}.controls{position:static}.metrics{grid-template-columns:repeat(3,1fr)}}@media(max-width:650px){header{padding:12px 14px}.connection{display:none}.layout{padding:12px}.metrics{grid-template-columns:repeat(2,1fr)}}
  </style>
</head>
<body>
  <header>
    <div class="brand"><div class="logo">₫</div><div><h1>Expense Approval Agent</h1><div class="sub">ReAct observability · read-only enterprise demo</div></div></div>
    <div class="connection">
      <div class="badge"><span class="dot" id="api-dot"></span><span id="api-state">Đang kiểm tra API</span></div>
      <div class="badge" id="provider">Provider: …</div><div class="badge" id="model">Model: …</div>
    </div>
  </header>
  <main class="layout">
    <aside class="card controls">
      <h2 class="title">Demo input</h2>
      <p class="help">Chọn kịch bản hoặc nhập yêu cầu để quan sát tuyến xử lý và bằng chứng từ tool.</p>
      <div class="level-map" id="level-map">
        <button class="level-card" data-level-mode="rule_based"><b>Level 1</b><span>Rule-based</span><small>Deterministic rules + tools</small></button>
        <button class="level-card" data-level-mode="chatbot"><b>Level 2</b><span>Chatbot</span><small>1 LLM call · no tools</small></button>
        <button class="level-card" data-level-mode="react"><b>Level 3</b><span>ReAct Agent</span><small>LLM loop + tools + guardrails</small></button>
        <button class="level-card active" data-level-mode="auto"><b>Level 4</b><span>Hybrid Router</span><small>Auto-select Level 2 or 3</small></button>
      </div>
      <label for="mode">Chế độ xử lý</label>
      <select id="mode"><option value="rule_based">Level 1 · Rule-based</option><option value="chatbot">Level 2 · Chatbot baseline</option><option value="react">Level 3 · ReAct Agent</option><option value="auto" selected>Level 4 · Hybrid Auto Router</option></select>
      <label for="question">Yêu cầu người dùng</label>
      <textarea id="question">Nhân viên E102 phòng Marketing đề nghị 12000000 VND cho sự kiện khách hàng, loại client_event và có hóa đơn. Hãy kiểm tra điều kiện duyệt và tuyến phê duyệt.</textarea>
      <button class="primary" id="run">▶ Chạy kịch bản</button>
      <label>Kịch bản nhanh</label>
      <div class="samples">
        <button class="sample" data-mode="rule_based" data-q="Nhân viên E102 phòng Marketing đề nghị 12000000 VND, loại client_event và có hóa đơn. Hãy kiểm tra phê duyệt."><b>Level 1 · Rule-based</b><span>Luồng cố định · không gọi LLM</span></button>
        <button class="sample" data-mode="chatbot" data-q="Chi phí hợp lệ khác hóa đơn hợp lệ như thế nào?"><b>Level 2 · Chatbot</b><span>Kiến thức chung · 1 LLM call · 0 tool</span></button>
        <button class="sample" data-mode="react" data-q="Nhân viên E102 phòng Marketing đề nghị 12000000 VND, loại client_event và có hóa đơn. Hãy kiểm tra phê duyệt."><b>Level 3 · ReAct Agent</b><span>Lập kế hoạch · 4 tool calls</span></button>
        <button class="sample" data-mode="auto" data-q="Khoản ăn tiếp khách 800000 VND thuộc loại meal và có hóa đơn. Khoản này có phù hợp chính sách không?"><b>Level 4 · Hybrid Router</b><span>Tự động chọn tuyến phù hợp</span></button>
      </div>
      <label>Tool registry · read-only</label><div class="chips" id="available-tools"></div>
    </aside>
    <div class="workspace">
      <section class="card">
        <div class="metrics">
          <div class="metric"><span>Level / Route</span><strong id="route">—</strong></div><div class="metric"><span>Status</span><strong id="status">Sẵn sàng</strong></div>
          <div class="metric"><span>Tool calls</span><strong id="tool-count">0</strong></div><div class="metric"><span>Iterations</span><strong id="iterations">0</strong></div><div class="metric"><span>Latency</span><strong id="latency">—</strong></div>
        </div>
        <div class="pipeline"><div class="node active">User input</div><div class="arrow">→</div><div class="node" id="pipe-route">Router</div><div class="arrow">→</div><div class="node" id="pipe-engine">LLM engine</div><div class="arrow">→</div><div class="node" id="pipe-tools">Tools / policy</div><div class="arrow">→</div><div class="node" id="pipe-final">Recommendation</div></div>
      </section>
      <section class="card">
        <div class="head"><h2>Kết quả khuyến nghị</h2><span class="outcome" id="outcome">CHƯA CHẠY</span></div>
        <div class="answer" id="answer">Chọn một kịch bản và nhấn “Chạy kịch bản”.</div><div class="evidence" id="tools-used"></div>
      </section>
      <section class="card">
        <div class="head"><div><h2>Decision & Tool Trace</h2><div class="sub">Bản ghi debug; không phải nhật ký phê duyệt thật.</div></div><button class="secondary" id="export" disabled>Xuất JSON</button></div>
        <div class="trace" id="trace"><div class="empty">Trace sẽ xuất hiện theo từng vòng ReAct.</div></div>
      </section>
    </div>
  </main>
  <script>
    const $=id=>document.getElementById(id);let lastResult=null;
    const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
    function pretty(value){if(typeof value==="string"){try{return JSON.stringify(JSON.parse(value),null,2)}catch{return value}}return JSON.stringify(value,null,2)}
    function outcome(answer,status){if(status==="error")return"ERROR";return String(answer||"").split(/\s|-/)[0].toUpperCase()||"UNKNOWN"}
    function rationale(response){const match=String(response||"").match(/Thought:\s*([\s\S]*?)(?=\nAction:|\nFinal Answer:|$)/i);return match?match[1].trim():"Mô hình đã trả về bước xử lý tiếp theo."}
    function syncLevel(mode){document.querySelectorAll("[data-level-mode]").forEach(card=>card.classList.toggle("active",card.dataset.levelMode===mode))}
    function pipeline(data){
      ["pipe-route","pipe-engine","pipe-tools","pipe-final"].forEach(id=>$(id).classList.remove("active"));
      const isRule=data.route==="RULE_BASED",isReact=data.route==="REACT_AGENT",isHybrid=data.level===4;
      $("pipe-route").classList.add("active");
      $("pipe-route").textContent=isHybrid?`Level 4 → Level ${data.routed_level}`:isRule?"Level 1 · Rules":isReact?"Level 3 · ReAct":"Level 2 · Chatbot";
      $("pipe-engine").classList.add("active");
      $("pipe-engine").textContent=isRule?"Deterministic rules":isReact?"ReAct loop":"Baseline LLM";
      if(data.tools_used?.length)$("pipe-tools").classList.add("active");
      $("pipe-tools").textContent=data.tools_used?.length?`${data.tools_used.length} tool calls`:"No tool";
      $("pipe-final").classList.add("active")
    }    function render(data){
      lastResult=data;syncLevel(data.selected_mode||$("mode").value);$("export").disabled=false;$("provider").textContent=`Provider: ${data.provider||"—"}`;$("model").textContent=`Model: ${data.model||"—"}`;$("route").textContent=data.level?`L${data.level} · ${data.route}`:(data.route||"—");$("status").textContent=data.status||"—";$("status").className=data.status==="completed"?"good":"warn";$("tool-count").textContent=data.tools_used?.length||0;$("iterations").textContent=data.trace?.length||0;$("latency").textContent=`${data.elapsed_ms??0} ms`;$("answer").textContent=data.answer||data.error||"Không có nội dung.";pipeline(data);
      const result=outcome(data.answer,data.status);$("outcome").textContent=result;$("outcome").className=`outcome ${result.toLowerCase()}`;
      $("tools-used").innerHTML=data.tools_used?.length?data.tools_used.map((name,i)=>`<span class="chip">${i+1}. ${esc(name)}</span>`).join(""):'<span class="badge">Không sử dụng dữ liệu nội bộ</span>';
      if(!data.trace?.length){$("trace").innerHTML='<div class="empty">Baseline hoàn tất bằng một lần gọi LLM, không cấp quyền truy cập tool.</div>';return}
      $("trace").innerHTML=data.trace.map(step=>{
        const kind=step.type==="action"?`Tool · ${step.tool}`:step.type==="final"?"Final recommendation":step.type==="guardrail"?"Guardrail":step.type==="error"?"Provider error":"Format recovery";
        const call=step.tool?`<div class="call"><div class="call-label">Action · tool call</div><pre>${esc(step.tool)}(${esc(pretty(step.arguments))})</pre></div>`:"";
        const obs=step.observation?`<div class="call obs"><div class="call-label">Observation · trusted local data</div><pre>${esc(pretty(step.observation))}</pre></div>`:"";
        return`<article class="step"><div class="index">${step.step}</div><div class="stepbox ${step.type==="error"?"errorbox":""}"><div class="stepbar"><span class="kind">${esc(kind)}</span><span class="latency">${step.latency_ms??0} ms</span></div><div class="decision"><strong>Quyết định:</strong> ${esc(rationale(step.model_response))}</div>${call}${obs}<details><summary>Phản hồi mô hình (raw)</summary><pre>${esc(step.model_response||"")}</pre></details></div></article>`
      }).join("")
    }
    async function run(){
      const button=$("run");button.disabled=true;button.innerHTML=$("mode").value==="rule_based"?'<span class="spinner"></span>Đang chạy rule Level 1…':'<span class="spinner"></span>Đang gọi mô hình thật…';$("status").textContent="Đang chạy";$("answer").textContent="Đang định tuyến và chờ phản hồi từ API…";$("trace").innerHTML='<div class="empty">Đang thu thập trace…</div>';
      try{const response=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mode:$("mode").value,question:$("question").value})});const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);render(data)}catch(error){render({status:"error",route:"—",answer:`Không thể chạy demo: ${error.message}`,tools_used:[],trace:[],elapsed_ms:0})}finally{button.disabled=false;button.textContent="▶ Chạy kịch bản"}
    }
    document.querySelectorAll("[data-level-mode]").forEach(card=>card.addEventListener("click",()=>{$("mode").value=card.dataset.levelMode;syncLevel(card.dataset.levelMode)}));$("mode").addEventListener("change",()=>syncLevel($("mode").value));document.querySelectorAll("[data-q]").forEach(button=>button.addEventListener("click",()=>{$("question").value=button.dataset.q;$("mode").value=button.dataset.mode;syncLevel(button.dataset.mode)}));syncLevel($("mode").value);$("run").addEventListener("click",run);$("question").addEventListener("keydown",event=>{if((event.ctrlKey||event.metaKey)&&event.key==="Enter")run()});
    $("export").addEventListener("click",()=>{if(!lastResult)return;const blob=new Blob([JSON.stringify(lastResult,null,2)],{type:"application/json"}),url=URL.createObjectURL(blob),anchor=document.createElement("a");anchor.href=url;anchor.download=`expense-agent-trace-${lastResult.request_id||"demo"}.json`;anchor.click();URL.revokeObjectURL(url)});
    fetch("/api/meta").then(response=>response.json()).then(data=>{$("provider").textContent=`Provider: ${data.provider}`;$("model").textContent=`Model: ${data.model}`;$("api-state").textContent=data.api_key_configured?"API key đã cấu hình":"Chưa có API key";$("api-dot").classList.toggle("live",data.api_key_configured);$("available-tools").innerHTML=data.available_tools.map(name=>`<span class="chip">${esc(name)}</span>`).join("")}).catch(()=>{$("api-state").textContent="Dashboard mất kết nối"});
  </script>
</body>
</html>
"""


def needs_agent(question: str) -> bool:
    """Route internal-data questions to the agent."""
    text = question.casefold()
    triggers = [
        "e10", "vnd", "policy", "chính sách", "ngân sách", "duyệt",
        "phê duyệt", "hóa đơn", "meal", "client_event", "budget", "receipt",
    ]
    return any(trigger in text for trigger in triggers)


def provider_meta(provider: Any) -> dict[str, Any]:
    """Return non-secret provider metadata for the UI."""
    names = {
        "OpenRouterProvider": "OpenRouter",
        "OpenAIProvider": "OpenAI",
        "GeminiProvider": "Google Gemini",
        "AnthropicProvider": "Anthropic",
        "MockProvider": "Mock / offline",
    }
    return {
        "provider": names.get(provider.__class__.__name__, provider.__class__.__name__),
        "model": getattr(provider, "model_name", "default"),
        "api_key_configured": bool(getattr(provider, "api_key", None))
        or provider.__class__.__name__ == "MockProvider",
        "available_tools": sorted(AVAILABLE_TOOLS),
        "max_iterations": MAX_ITERATIONS,
    }


def _provider_error(response: str) -> bool:
    return response.lstrip().startswith(
        (
            "[OpenRouter API Error", "[OpenRouter Exception", "[OpenRouter Error",
            "[OpenAI Exception", "[OpenAI Error", "[Gemini Exception",
            "[Gemini Error", "[Anthropic Exception", "[Anthropic Error",
        )
    )


def _requires_human_approval(trace: list[dict[str, Any]]) -> bool:
    """Detect authoritative evidence that a human approval step remains."""
    for item in trace:
        observation = item.get("observation")
        if not isinstance(observation, str):
            continue
        try:
            payload = json.loads(observation)
        except json.JSONDecodeError:
            continue
        if payload.get("human_approval_required") is True:
            return True
    return False


def run_debug_react(question: str, provider: Any) -> dict[str, Any]:
    """Run ReAct while preserving a UI-friendly execution trace."""
    history = f"Question: {question}"
    trace: list[dict[str, Any]] = []
    action_counts: dict[str, int] = {}

    for step in range(1, MAX_ITERATIONS + 1):
        started = time.perf_counter()
        response = provider.generate(history, system_prompt=REACT_SYSTEM_PROMPT)
        latency_ms = round((time.perf_counter() - started) * 1000)
        if _provider_error(response):
            trace.append(
                {"step": step, "type": "error", "model_response": response, "latency_ms": latency_ms}
            )
            return {"status": "error", "answer": response, "tools_used": [], "trace": trace}

        parsed = parse_agent_response(response)
        if parsed["type"] == "final":
            answer = parsed["answer"]
            record = {
                "step": step, "type": "final", "model_response": response,
                "answer": answer, "latency_ms": latency_ms,
            }
            if answer.startswith("APPROVE") and _requires_human_approval(trace):
                answer = (
                    "ESCALATE - Các kiểm tra tự động đã đạt, nhưng tuyến phê duyệt "
                    "yêu cầu người có thẩm quyền xác nhận trước khi chi."
                )
                record.update(
                    {
                        "type": "guardrail",
                        "answer": answer,
                        "observation": (
                            "Guardrail: human_approval_required=true; "
                            "chuẩn hóa APPROVE thành ESCALATE."
                        ),
                    }
                )
            if answer.startswith(("APPROVE", "ESCALATE")) and not any(
                item.get("tool") for item in trace
            ):
                observation = json.dumps(
                    {"ok": False, "error": "Kết luận cần bằng chứng từ tool trước khi trả lời."},
                    ensure_ascii=False,
                )
                record.update({"type": "guardrail", "observation": observation})
                trace.append(record)
                history += f"\n{response}\nObservation: {observation}"
                continue
            trace.append(record)
            return {
                "status": "completed",
                "answer": answer,
                "tools_used": [item["tool"] for item in trace if item.get("tool")],
                "trace": trace,
            }

        if parsed["type"] == "invalid":
            observation = json.dumps({"ok": False, "error": parsed["error"]}, ensure_ascii=False)
            trace.append(
                {
                    "step": step, "type": "invalid", "model_response": response,
                    "observation": observation, "latency_ms": latency_ms,
                }
            )
            history += f"\n{response}\nObservation: {observation}"
            continue

        fingerprint = json.dumps(
            [parsed["tool"], parsed["arguments"]], ensure_ascii=False, sort_keys=True
        )
        action_counts[fingerprint] = action_counts.get(fingerprint, 0) + 1
        if action_counts[fingerprint] > MAX_REPEATED_ACTIONS:
            answer = "NEED_MORE_INFO - Agent lặp lại cùng một Action quá số lần cho phép."
            trace.append(
                {
                    "step": step, "type": "guardrail", "model_response": response,
                    "tool": parsed["tool"], "arguments": parsed["arguments"],
                    "observation": answer, "latency_ms": latency_ms,
                }
            )
            return {
                "status": "guardrail", "answer": answer,
                "tools_used": [item["tool"] for item in trace if item.get("tool")],
                "trace": trace,
            }

        observation = execute_tool(parsed["tool"], parsed["arguments"])
        trace.append(
            {
                "step": step, "type": "action", "model_response": response,
                "tool": parsed["tool"], "arguments": parsed["arguments"],
                "observation": observation, "latency_ms": latency_ms,
            }
        )
        history += f"\n{response}\nObservation: {observation}"

    return {
        "status": "guardrail",
        "answer": f"NEED_MORE_INFO - Đã đạt MAX_ITERATIONS={MAX_ITERATIONS}; dừng an toàn.",
        "tools_used": [item["tool"] for item in trace if item.get("tool")],
        "trace": trace,
    }


def answer_question(question: str, mode: str, provider: Any) -> dict[str, Any]:
    """Route one request and return a complete debug payload."""
    started = time.perf_counter()
    selected = mode if mode in {"rule_based", "chatbot", "react"} else "auto"
    level_by_mode = {"rule_based": 1, "chatbot": 2, "react": 3, "auto": 4}
    level_names = {
        1: "Rule-based",
        2: "Chatbot baseline",
        3: "ReAct Agent",
        4: "Hybrid Auto Router",
    }
    level = level_by_mode[selected]
    if selected == "rule_based":
        route = "RULE_BASED"
    elif selected == "react":
        route = "REACT_AGENT"
    elif selected == "chatbot":
        route = "CHATBOT"
    else:
        route = "REACT_AGENT" if needs_agent(question) else "CHATBOT"

    if route == "RULE_BASED":
        result = run_rule_based(question, execute_tool)
    elif route == "CHATBOT":
        answer = run_baseline_chatbot(question, provider, verbose=False)
        result: dict[str, Any] = {
            "status": "error" if _provider_error(answer) else "completed",
            "answer": answer, "tools_used": [], "trace": [],
        }
    else:
        result = run_debug_react(question, provider)

    metadata = provider_meta(provider)
    if route == "RULE_BASED":
        metadata.update(
            {
                "provider": "Local Rules",
                "model": "rule-engine-v1",
                "api_key_configured": True,
            }
        )
    result.update(metadata)
    result.update(
        {
            "route": route,
            "level": level,
            "level_name": level_names[level],
            "selected_mode": selected,
            "routed_level": {
                "RULE_BASED": 1,
                "CHATBOT": 2,
                "REACT_AGENT": 3,
            }[route],
            "request_id": uuid.uuid4().hex[:10],
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }
    )
    return result


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP API and static dashboard handler."""

    provider: Any = None

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/meta":
            self._json(provider_meta(self.provider))
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/chat":
            self._json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            question = str(payload.get("question", "")).strip()
            mode = str(payload.get("mode", "auto")).strip().lower()
            if not question:
                self._json({"error": "Vui lòng nhập yêu cầu."}, 400)
                return
            self._json(answer_question(question, mode, self.provider))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json({"error": "Request body phải là JSON UTF-8 hợp lệ."}, 400)
        except Exception as exc:
            self._json({"error": f"Dashboard error: {exc}"}, 500)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the expense agent dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()

    DashboardHandler.provider = get_llm_provider(args.provider)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    meta = provider_meta(DashboardHandler.provider)
    print(
        f"Dashboard: http://{args.host}:{args.port} | {meta['provider']} | {meta['model']}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
