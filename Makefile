.PHONY: help lint check-deps check req req-dev sync deps fix test ai-test ai-autofix ai-review

help:
	@echo "Available commands:"
	@echo "  make check       - Run all checks (Ruff, MyPy, Deptry)"
	@echo "  make fix         - Run small fixes with Ruff"
	@echo "  make lint        - Run linter and type checker only"
	@echo "  make test        - Run all pytest unit tests"
	@echo "  make deps        - Update and sync all dependencies"
	@echo "  make ai-test     - Generate tests for a specific file (use FILE=path)"
	@echo "  make ai-autofix  - Let Gemini run check and fix errors automatically"

# --- ПЕРЕВІРКА КОДУ ---

fix:
	ruff check . --fix

lint:
	ruff check .
	mypy . 

check-deps:
	deptry .

check: lint check-deps

test:
	pytest tests/

# --- РОБОТА ІЗ ЗАЛЕЖНОСТЯМИ (pip-tools) ---

req:
	pip-compile requirements.in

req-dev:
	pip-compile requirements-dev.in

sync:
	pip-sync requirements.txt requirements-dev.txt

deps: req req-dev sync

# --- GEMINI CLI AUTOMATION ---

# Згенерувати тести для конкретного файлу
ai-test:
	gemini ask "Generate comprehensive pytest unit tests for $(FILE). Ensure all external dependencies are properly mocked."

# Автономний цикл: ШІ сам запускає лінтери, бачить помилки і фіксить їх, поки make check не стане зеленим
ai-autofix:
	gemini run "Execute 'make check'. If it fails, analyze the output, fix the errors in code, and repeat until 'make check' passes successfully."

# ШІ-рев'ю перед комітом
ai-review:
	gemini ask "Review the current git diff. Check for architectural flaws, memory leaks, and strict typing violations."