"""Модуль тестів для діалогу перегляду логів (LogDialog)."""

from typing import Any, Generator
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt

from app.models.detection_event import DetectionEvent
from app.models.log_entries import LogEntry, LogType
from app.models.source_type import SourceType
from app.services.log_service import LogSession
from app.widgets.log_dialog import LogDialog


@pytest.fixture
def mock_log_service() -> MagicMock:
    """Створює мок-об'єкт сервісу логів."""
    service = MagicMock()
    # Імітуємо наявність однієї сесії
    session = LogSession(filename="session_2026-05-30.jsonl", label="30.05.2026 12:00")
    service.get_available_sessions.return_value = [session]

    # Імітуємо дані сесії
    event = DetectionEvent(
        id="test_id",
        type=SourceType.RF,
        name="Target",
        object_class="drone",
        confidence=0.9,
        timestamp="2026-05-30T12:00:00",
        distance_km=1.0,
        angle=45.0,
        frequency_hz=2.4e9,
    )
    entry = LogEntry(
        type=LogType.DETECTION, timestamp="2026-05-30T12:00:05", payload=event
    )
    service.load_session_data.return_value = [entry]

    return service


@pytest.fixture
def mock_bg_service() -> MagicMock:
    """Створює мок-об'єкт сервісу фонових зображень."""
    return MagicMock()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Створює мок-об'єкт налаштувань програми."""
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def log_dialog(
    qtbot: Any,
    mock_log_service: MagicMock,
    mock_bg_service: MagicMock,
    mock_settings: MagicMock,
) -> Generator[LogDialog, None, None]:
    """Ініціалізує та повертає екземпляр LogDialog."""
    from app.models.object_class import ObjectClass

    classes: list[ObjectClass] = []
    dialog = LogDialog(mock_log_service, mock_bg_service, classes, mock_settings)
    qtbot.addWidget(dialog)
    yield dialog
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.removeTranslator(dialog.translator)


def test_initial_load(log_dialog: LogDialog, mock_log_service: MagicMock) -> None:
    """Перевіряє завантаження сесій та даних у таблицю."""
    assert log_dialog.ui.cmbSessions.count() == 1
    assert log_dialog.ui.cmbSessions.currentText() == "30.05.2026 12:00"

    assert log_dialog.ui.tableLogs.rowCount() == 1
    assert "Target" in log_dialog.ui.tableLogs.item(0, 2).text()


def test_tab_switching(log_dialog: LogDialog, qtbot: Any) -> None:
    """Перевіряє перемикання вкладок та оновлення графіків."""
    log_dialog.ui.tabWidget.setCurrentIndex(1)
    assert log_dialog.ui.tabWidget.currentIndex() == 1

    assert log_dialog.chart_gen.data is not None


def test_filter_by_name(log_dialog: LogDialog, qtbot: Any) -> None:
    """Перевіряє фільтрацію логів за назвою."""
    # Сценарій 1: Фільтр, що не дає результатів
    log_dialog.ui.inpFilterName.setText("NonExistent")
    qtbot.mouseClick(log_dialog.ui.btnApplyFilters, Qt.MouseButton.LeftButton)
    assert log_dialog.ui.tableLogs.rowCount() == 0

    # Сценарій 2: Фільтр, що відповідає наявним даним
    log_dialog.ui.inpFilterName.setText("Target")
    qtbot.mouseClick(log_dialog.ui.btnApplyFilters, Qt.MouseButton.LeftButton)
    assert log_dialog.ui.tableLogs.rowCount() == 1


def test_reset_filters(log_dialog: LogDialog, qtbot: Any) -> None:
    """Перевіряє скидання встановлених фільтрів."""
    log_dialog.ui.inpFilterName.setText("SomeFilter")
    log_dialog.ui.inpDistMin.setValue(100)

    qtbot.mouseClick(log_dialog.ui.btnResetFilters, Qt.MouseButton.LeftButton)

    assert log_dialog.ui.inpFilterName.text() == ""
    assert log_dialog.ui.inpDistMin.value() == 0
    assert log_dialog.ui.tableLogs.rowCount() == 1


def test_session_change_triggers_load(
    log_dialog: LogDialog, mock_log_service: MagicMock, qtbot: Any
) -> None:
    """Перевіряє перевантаження даних при виборі іншої сесії."""
    # Очищуємо дані перед тестом
    log_dialog.all_entries = []

    # Додаємо нову сесію в ComboBox
    log_dialog.ui.cmbSessions.addItem("New Session", "new.jsonl")
    log_dialog.ui.cmbSessions.setCurrentIndex(1)

    assert len(log_dialog.all_entries) == 1


def test_background_navigation_visibility(log_dialog: LogDialog) -> None:
    """Перевіряє відображення панелі керування фоном."""
    log_dialog.ui.tabWidget.setCurrentIndex(2)  # Вкладка "Аналіз об'єкта"

    # Режим "Шлях" (Path) - контроль фону має бути прихований
    log_dialog.ui.cmbTargetType.setCurrentIndex(0)
    assert log_dialog.ui.grpBackgroundControl.isHidden() is True

    # Режим "Спектр" (Spectrum) - має бути видимий
    if log_dialog.ui.cmbTargetObject.count() > 0:
        log_dialog.ui.cmbTargetObject.setCurrentIndex(0)
        log_dialog.ui.cmbTargetType.setCurrentIndex(2)
        assert log_dialog.ui.grpBackgroundControl.isHidden() is False
