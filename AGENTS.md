# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python teaching lab comparing four levels of conversational AI. Core implementation lives in `src/`: `app.py` runs the main demonstration, `providers.py` adapts supported LLM providers, `tools.py` defines callable tools, and `prompts.py` contains prompts and guardrails. Standalone examples are under `src/ai_levels/`. Test scenarios are data-driven in `config/test_cases.json`; there is currently no automated `tests/` suite. Lab instructions and evaluation notes belong in `docs/`.

Keep provider-specific behavior inside `providers.py`, reusable tool functions in `tools.py`, and orchestration in `app.py`. Do not commit generated caches or local environments.

## Build, Test, and Development Commands

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Use `LLM_PROVIDER=mock` in `.env` for offline development, or configure one provider API key. Run the complete comparison with `python src/app.py`. Run an isolated example with `python src/ai_levels/level3_reactive_agent.py`. Before submitting, compile all modules with `python -m compileall src`.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation and UTF-8 source files. Use `snake_case` for functions, variables, and modules; `PascalCase` for classes; and `UPPER_SNAKE_CASE` for constants such as `MAX_ITERATIONS`. Add type hints to public functions and concise docstrings to providers and tools. Preserve the existing separation between prompts, tools, providers, and orchestration. No formatter or linter is configured, so keep imports grouped and remove trailing whitespace manually.

## Testing Guidelines

Treat every entry in `config/test_cases.json` as a behavioral acceptance case. Changes to tools or guardrails should cover direct queries, multi-tool flows, invalid inputs, and the iteration limit. Add automated tests under `tests/` using names like `test_tools.py` and functions like `test_get_weather_unknown_city`; run them with `python -m pytest` after adding `pytest` as a development dependency. Record representative traces and evaluation findings in `docs/trace_eval.md`.

## Commit & Pull Request Guidelines

Recent history uses concise, imperative subjects such as `Add multi-provider adapter` and `Clarify LLM_MODEL options`; follow that pattern and keep each commit focused. Pull requests should explain the behavior changed, list commands or scenarios tested, link the relevant issue or lab task, and include sample console output when agent traces change. Never commit `.env`, API keys, or other credentials.
