# SDR_Pi Project Instructions

## 1. Project Context & Architecture

- **Domain:** Passive radar and radio monitoring system for UAV detection.
- **Hardware:** Raspberry Pi + Pluto SDR (Server) <-> Desktop PC (Client).
- **Tech Stack:** Python 3.12+, PyQt6 (GUI), asyncio/qasync, NumPy (DSP & Math), SQLAlchemy (SQLite).
- **Directory Structure:**
  - `app/` — Desktop Client (GUI, PyQt6, services, models).
  - `pi_server/` — Raspberry Pi Server (TCP Server, SQLite DB, Hardware stubs).
  - `tests/` — Юніт, інтеграційні та E2E тести (розділені по відповідних підпапках).
- **Communication:** TCP Sockets transmitting JSON payloads.
  - Client service: `PiNetworkService`
  - Server service: `PiServerService`

## 2. Coding Standards

- **Typing:** Enforce strict PEP 484 typing (`mypy`). Always use `-> None` for empty functions.
- **Language:** Code comments, docstrings, and generated documentation MUST be strictly in **Ukrainian**. Git commit messages also in **Ukrainian** (Conventional Commits: `feat: ...`, `fix: ...`).
- **Formatting:** Managed by `ruff` (`make format`, `make fix`).
- **Architecture:** Services should use Dependency Injection where possible. UI logic should be separated from Business Logic.

## 3. Testing Rules

- **Framework:** `pytest`, `pytest-qt` (for GUI testing).
- **Isolation:** Never test real physical hardware. Always mock hardware dependencies (`unittest.mock`).
- **Database:** Use `sqlite:///:memory:` with `StaticPool` for database testing.
- **Pattern:** Strictly follow the AAA (Arrange, Act, Assert) testing pattern.
- **Assertions:** Add descriptive English messages to assertions for better diagnostics (e.g., `assert value == 1, "Expected value to be 1"`).
- **Asynchrony:** Use `qtbot.wait_signal` or `qtbot.wait_until` to handle asynchronous operations and signals in tests. Do not use blocking `time.sleep` unless absolutely necessary.
- **E2E Testing:** E2E tests (`tests/e2e/`) should simulate real user workflows using `qtbot` and an in-memory `pi_server` instance.

## 4. Workflows & Validation (CRITICAL)

- **Dependency Management:** To add new packages, edit `requirements.in` or `requirements-dev.in`. Always use `make deps` to recompile and synchronize dependencies (this utilizes `pip-compile` and `pip-sync`). Never use direct `pip install <package>`.
- **Git Restrictions:** You are STRICTLY FORBIDDEN from executing any Git commands (`git commit`, `git add`, `git push`, `git checkout` тощо). All Git operations are managed exclusively by the user. You may only analyze `git diff` when requested.
- **Code Validation:** Before marking any code change task as complete, **you MUST ensure the code is valid**:
  1. Use `make format` to style code.
  2. Use `make check` to run linters (`ruff`) and type checkers (`mypy`).
- **Test Validation:** When creating or modifying test files, you **Analyse and MUST immediately run `pytest`** (or appropriate `make test-*` command) on the modified file to verify its correctness. Do not mark a task as complete if tests are failing.
