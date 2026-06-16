"""Юніт-тести для модуля конфігурації логування logging_config."""

import logging
import sys
from pathlib import Path
from typing import Generator

import pytest

from app.core.logging_config import get_logger, setup_logging


@pytest.fixture
def restore_logging() -> Generator[None, None, None]:
    """Фікстура для відновлення стану логування після кожного тесту."""
    # Зберігаємо оригінальні хендлери та рівень root-логера
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers.copy()
    original_level = root_logger.level

    yield

    # Відновлюємо оригінальні налаштування
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


def test_get_logger_returns_correct_logger() -> None:
    """Тест перевіряє, що get_logger повертає логер з правильним іменем."""
    # Arrange
    logger_name = "test_logger_name"

    # Act
    logger = get_logger(logger_name)

    # Assert
    assert isinstance(logger, logging.Logger), "Should return a logging.Logger instance"
    assert logger.name == logger_name, f"Expected logger name to be '{logger_name}'"


def test_setup_logging_default(restore_logging: None) -> None:
    """Тест перевіряє базове налаштування логування зі StreamHandler."""
    # Arrange
    test_level = logging.DEBUG

    # Act
    setup_logging(level=test_level)
    root_logger = logging.getLogger()

    # Assert
    assert root_logger.level == test_level, f"Expected log level to be {test_level}"
    assert len(root_logger.handlers) >= 1, "Expected at least one handler configured"

    # Перевіряємо наявність StreamHandler, який направляє в stdout
    stream_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout
    ]
    assert len(stream_handlers) == 1, (
        "Expected exactly one StreamHandler pointing to stdout"
    )


def test_setup_logging_with_file(tmp_path: Path, restore_logging: None) -> None:
    """Тест перевіряє налаштування логування із записом у файл."""
    # Arrange
    log_file_path = tmp_path / "test_app.log"
    test_level = logging.INFO
    test_message = "Test log message for file handler"
    logger = get_logger("test_file_logger")

    # Act
    setup_logging(level=test_level, log_file=str(log_file_path))
    logger.info(test_message)

    # Спочатку закриваємо хендлери, щоб звільнити файл перед читанням
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.close()

    # Assert
    assert log_file_path.exists(), "Expected log file to be created"

    log_content = log_file_path.read_text(encoding="utf-8")
    assert test_message in log_content, (
        f"Expected '{test_message}' to be written to log file"
    )
    assert "INFO" in log_content, (
        "Expected log level 'INFO' to be present in log file content"
    )
