"""Модуль для запуску та аналізу результатів тестування проєкту SDR_Pi."""

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Налаштування UTF-8 кодування для Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")


class Colors:
    """ANSI-коди кольорів для стилізації термінального виводу."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


@dataclass
class TestGroup:
    """
    ### Тестова група

    Зберігає інформацію про логічне об'єднання тестів.

    - **name**: Назва (напр. "Unit: Models").
    - **path**: Шлях до файлів.
    - **description**: Опис групи.
    """

    name: str
    path: str
    description: str


def run_group(
    group: TestGroup, collect_cov: bool = False
) -> Tuple[int, List[str], List[str]]:
    """Запускає групу тестів через pytest та повертає статус і списки проблем."""
    print(
        f"\n{Colors.BOLD}{Colors.OKBLUE}=== Running Group: {group.name} ==={Colors.ENDC}"
    )
    print(f"{Colors.OKCYAN}{group.description}{Colors.ENDC}")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        group.path,
        "-ra",
        "--tb=short",
        "--no-header",
    ]

    if collect_cov:
        cmd.extend(["--cov=app", "--cov=pi_server", "--cov-append", "--cov-report="])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        universal_newlines=True,
        env=env,
    )

    failures = []
    warnings = []

    in_warnings_summary = False
    in_short_summary = False
    in_failures_section = False

    current_warning_test = None
    current_failure_test = None
    failure_details: Dict[str, List[str]] = {}

    if process.stdout:
        for line in process.stdout:
            print(line, end="", flush=True)
            stripped = line.strip()

            # Аналіз FAILURES
            if re.match(r"^_{3,}.+_{3,}$", stripped):
                in_failures_section = True
                test_name = stripped.strip("_ ").split()[0]
                current_failure_test = test_name
                failure_details[current_failure_test] = []
                continue

            if in_failures_section:
                if stripped.startswith("E ") or stripped.startswith("E  "):
                    err_msg = stripped[1:].strip()
                    if current_failure_test and err_msg:
                        failure_details[current_failure_test].append(err_msg)
                elif line.startswith("===") or (
                    line.startswith("---") and "Captured" not in line
                ):
                    in_failures_section = False
                    current_failure_test = None

            # Аналіз WARNINGS
            if "=== warnings summary ===" in line:
                in_warnings_summary = True
                in_failures_section = False
                in_short_summary = False
                continue

            if in_warnings_summary:
                if line.startswith("tests/") and "::" in line:
                    current_warning_test = stripped
                elif current_warning_test and stripped and not line.startswith("==="):
                    warnings.append(
                        f"{current_warning_test}\n    {Colors.WARNING}└─ {stripped}{Colors.ENDC}"
                    )
                    current_warning_test = None
                elif line.startswith("==="):
                    in_warnings_summary = False

            # Аналіз SHORT SUMMARY
            if "=== short test summary info ===" in line:
                in_short_summary = True
                in_failures_section = False
                in_warnings_summary = False
                continue

            if in_short_summary:
                if line.startswith("FAILED ") or line.startswith("ERROR "):
                    parts = line.split(" ", 1)
                    if len(parts) > 1:
                        test_id = parts[1].split(" - ")[0].strip()
                        test_func_name = test_id.split("::")[-1]

                        detail = "No details"
                        if (
                            test_func_name in failure_details
                            and failure_details[test_func_name]
                        ):
                            detail = " | ".join(failure_details[test_func_name])
                        elif " - " in parts[1]:
                            detail = parts[1].split(" - ", 1)[1].strip()

                        failures.append(
                            f"{test_id}\n    {Colors.FAIL}└─ {detail}{Colors.ENDC}"
                        )
                elif line.startswith("==="):
                    in_short_summary = False

    process.wait()
    return process.returncode, failures, warnings


def main() -> None:
    """Точка входу для запуску всіх груп тестів та формування звіту."""
    collect_cov = "--cov" in sys.argv

    if collect_cov:
        subprocess.run([sys.executable, "-m", "coverage", "erase"])

    groups = [
        TestGroup(
            "Bootstrap", "tests/test_main.py", "Тестування ініціалізації та точки входу"
        ),
        TestGroup(
            "Unit: Models", "tests/models/", "Тестування структур даних та серіалізації"
        ),
        TestGroup(
            "Unit: Services", "tests/services/", "Тестування бізнес-логіки сервісів"
        ),
        TestGroup(
            "Unit: Utils", "tests/utils/", "Тестування допоміжних функцій та математики"
        ),
        TestGroup(
            "Unit: Validators", "tests/validators/", "Тестування валідації вводу"
        ),
        TestGroup(
            "Unit: Widgets", "tests/widgets/", "Тестування окремих UI компонентів"
        ),
        TestGroup("Unit: Core", "tests/core/", "Тестування ядра логіки додатку"),
        TestGroup(
            "Integration", "tests/integration/", "Тестування взаємодії Клієнт-Сервер"
        ),
        TestGroup(
            "E2E: Full Scenarios",
            "tests/e2e/",
            "Тестування повних сценаріїв використання",
        ),
    ]

    print(
        f"\n{Colors.HEADER}{Colors.BOLD}SDR_Pi Test Suite Runner (with Coverage Support){Colors.ENDC}"
    )
    print("=" * 80)

    start_time = time.time()
    failed_groups = []
    all_failures = []
    all_warnings = []

    for group in groups:
        exit_code, group_fails, group_warns = run_group(group, collect_cov=collect_cov)
        if exit_code != 0:
            failed_groups.append(group.name)
        all_failures.extend(group_fails)
        all_warnings.extend(group_warns)

    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 80)
    print(f"{Colors.BOLD}{Colors.UNDERLINE}FINAL SUMMARY REPORT{Colors.ENDC}")
    print("=" * 80)
    print(f"Total tests duration: {duration:.2f}s")

    if all_warnings:
        print(
            f"\n{Colors.WARNING}{Colors.BOLD}⚠ WARNINGS ({len(all_warnings)}):{Colors.ENDC}"
        )
        unique_warnings = []
        seen = set()
        for w in all_warnings:
            if w not in seen:
                unique_warnings.append(w)
                seen.add(w)
        for w in unique_warnings:
            print(f"  {w}")

    if all_failures:
        print(
            f"\n{Colors.FAIL}{Colors.BOLD}✘ FAILURES ({len(all_failures)}):{Colors.ENDC}"
        )
        for f in all_failures:
            print(f"  {f}")

    print("\n" + "-" * 80)
    if not failed_groups:
        print(
            f"{Colors.OKGREEN}{Colors.BOLD}✅ ALL TEST GROUPS PASSED SUCCESSFULLY!{Colors.ENDC}"
        )
    else:
        print(
            f"{Colors.FAIL}{Colors.BOLD}❌ SOME GROUPS FAILED ({len(failed_groups)}/{len(groups)}):{Colors.ENDC}"
        )
        for gname in failed_groups:
            print(f"  - {gname}")

    if collect_cov:
        print("\n" + "=" * 80)
        print(f"{Colors.BOLD}GENERATING COVERAGE REPORTS{Colors.ENDC}")
        print("=" * 80)

        subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "report",
                "--include=app/*,pi_server/*",
                "-m",
            ]
        )

        os.makedirs("tests/coverage_html", exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "html",
                "-d",
                "tests/coverage_html",
                "--include=app/*,pi_server/*",
            ]
        )

        print(f"\n{Colors.OKGREEN}✅ Terminal report generated above.{Colors.ENDC}")
        print(
            f"{Colors.OKGREEN}✅ HTML report generated at: {Colors.BOLD}tests/coverage_html/index.html{Colors.ENDC}"
        )

    print(
        "\n"
        + f"{Colors.WARNING}TIP: Run 'pytest --lf' to re-run only failed tests.{Colors.ENDC}"
    )

    if failed_groups:
        sys.exit(1)


if __name__ == "__main__":
    main()
