.PHONY: help lint check-deps check req req-dev sync deps format fix test ai-test ai-autofix ai-review

help:
	@echo "Available commands:"
	@echo "  make format      - Auto-format code with Ruff formatter"
	@echo "  make fix         - Run small fixes with Ruff linter"
	@echo "  make check       - Run formatting, linting, MyPy, and Deptry"
	@echo "  make test        - Run all pytest unit tests (structured)"
	@echo "  make test-raw    - Run standard pytest output"
	@echo "  make coverage    - Run all tests and measure code coverage"
	@echo "  make cov-report  - Open visual HTML coverage report in browser"
	@echo "  make ai-test     - Generate tests for a specific file (use FILE=path)"
	@echo "  make ai-autofix  - Let Gemini format, check, and fix errors automatically"

# --- ПЕРЕВІРКА ТА ФОРМАТУВАННЯ КОДУ ---

# 1. Форматування (вирівнює стиль, відступи, лапки)
format:
	ruff format .

# 2. Швидкі автофікси правил лінтера
fix:
	ruff check . --fix

# 3. Чистий лінтер та статичний аналіз типів
lint:
	ruff check .
	mypy . 

# 4. Перевірка залежностей
check-deps:
	deptry .

# Головна команда перевірки (тепер спочатку САМА форматує код, а потім перевіряє)
check: format lint check-deps

# --- ТЕСТИ ---
test:
	python tests/run_tests.py

test-raw:
	pytest tests/

coverage:
	python tests/run_tests.py --cov

cov-report:
	cmd /c start tests/coverage_html/index.html

# --- РОБОТА ІЗ ЗАЛЕЖНОСТЯМИ (pip-tools) ---
req:
	pip-compile requirements.in

req-dev:
	pip-compile requirements-dev.in

sync:
	pip-sync requirements.txt requirements-dev.txt

deps: req req-dev sync

# --- GEMINI CLI AUTOMATION ---

ai-test:
	gemini ask "Generate comprehensive pytest unit tests for $(FILE). Ensure all external dependencies are properly mocked."

ai-autofix:
	gemini run "Execute 'make check'. If it fails, analyze the output, fix the errors in code, and repeat until 'make check' passes successfully."

ai-review:
	gemini ask "Review the current git diff. Check for architectural flaws, memory leaks, and strict typing violations."