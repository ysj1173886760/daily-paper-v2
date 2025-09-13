# Repository Guidelines

## Project Structure & Module Organization
- `daily_paper/`: Core package
  - `flow/`: End-to-end flows (e.g., `daily_report_flow.py`)
  - `nodes/`: Reusable processing nodes (suffix `_node.py`)
  - `templates/`: Analysis/render templates
  - `utils/`, `model/`: Helpers and data models
- `config/`: YAML configs (e.g., `rag.yaml`, `kg.yaml`, `test.yaml`)
- `tests/`: Smoke/integration tests (`test_*.py`)
- `data/`, `papers/`, `arxiv_data/`: Local artifacts and outputs
- `docs/`, `github-pages-site/`, `assets/`: Documentation and site content
- Entry point: `main.py`

## Build, Test, and Development Commands
- Setup venv: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run pipeline: `python main.py --config_path config/rag.yaml`
- Alternate config: `python main.py --config_path config/kg.yaml`
- Format code: `make format` (runs `black daily_paper`)
- Run a test script: `python tests/test_daily_report.py --config config/test.yaml`
- Optional (if pytest installed): `pytest -q`

## Coding Style & Naming Conventions
- Python, PEP 8, 4-space indentation; prefer type hints where reasonable.
- Files/modules: `snake_case.py`; classes: `PascalCase`; functions/vars: `snake_case`; constants: `UPPER_SNAKE_CASE`.
- Node modules end with `_node.py`; node classes use `XxxNode`.
- Keep functions small and composable; log via `daily_paper.utils.logger`.

## Testing Guidelines
- Tests live in `tests/` and use `test_*.py` naming.
- Many tests are integration-style; `config/test.yaml` is required. Networked tests (Feishu/arXiv/LLM) should be skipped or mocked when secrets are absent.
- Aim to cover new nodes/flows with focused tests; prefer deterministic inputs.

## Commit & Pull Request Guidelines
- Commits: short, imperative, scoped (e.g., `add design docs`, `fix push logic`).
- PRs include: concise description, linked issue, config notes, and relevant logs/screenshots (e.g., Feishu push result, RSS output snippet).
- Checklist: `make format` clean, tests/scripts pass, no large data files or secrets.

## Security & Configuration Tips
- Do not hardcode secrets. Store LLM keys and Feishu webhooks only in local, untracked configs (see `config/test.yaml`).
- Review generated artifacts in `data/`/`papers/` before publishing; sanitize sensitive content.
- For RSS/GitHub Pages, verify URLs and tokens in config before enabling publish nodes.

