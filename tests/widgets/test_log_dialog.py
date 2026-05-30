"""
Тести для діалогу логів (LogDialog).
"""

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt

from app.models.detection_event import DetectionEvent
from app.models.log_entries import LogEntry, LogType
from app.models.source_type import SourceType
from app.services.log_service import LogSession
from app.widgets.log_dialog import LogDialog


@pytest.fixture
def mock_log_service():
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
def mock_bg_service():
    return MagicMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def log_dialog(qtbot, mock_log_service, mock_bg_service, mock_settings):
    """Фікстура для ініціалізації LogDialog."""
    classes = []  # Можна додати тестові класи за потреби
    dialog = LogDialog(mock_log_service, mock_bg_service, classes, mock_settings)
    qtbot.addWidget(dialog)
    yield dialog
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.removeTranslator(dialog.translator)


def test_initial_load(log_dialog, mock_log_service):
    """Тест початкового завантаження сесій та даних."""
    assert log_dialog.ui.cmbSessions.count() == 1
    assert log_dialog.ui.cmbSessions.currentText() == "30.05.2026 12:00"

    # Перевіряємо наповнення таблиці
    assert log_dialog.ui.tableLogs.rowCount() == 1
    assert "Target" in log_dialog.ui.tableLogs.item(0, 2).text()


def test_tab_switching(log_dialog, qtbot):
    """Тест перемикання вкладок."""
    # Перемикаємо на вкладку графіків
    log_dialog.ui.tabWidget.setCurrentIndex(1)
    assert log_dialog.ui.tabWidget.currentIndex() == 1

    # Має оновитися загальний графік
    assert log_dialog.chart_gen.data is not None


def test_filter_by_name(log_dialog, qtbot):
    """Тест фільтрації за назвою/ID."""
    log_dialog.ui.inpFilterName.setText("NonExistent")
    qtbot.mouseClick(log_dialog.ui.btnApplyFilters, Qt.MouseButton.LeftButton)

    assert log_dialog.ui.tableLogs.rowCount() == 0

    log_dialog.ui.inpFilterName.setText("Target")
    qtbot.mouseClick(log_dialog.ui.btnApplyFilters, Qt.MouseButton.LeftButton)
    assert log_dialog.ui.tableLogs.rowCount() == 1


def test_reset_filters(log_dialog, qtbot):
    """Тест скидання фільтрів."""
    log_dialog.ui.inpFilterName.setText("SomeFilter")
    log_dialog.ui.inpDistMin.setValue(100)

    qtbot.mouseClick(log_dialog.ui.btnResetFilters, Qt.MouseButton.LeftButton)

    assert log_dialog.ui.inpFilterName.text() == ""
    assert log_dialog.ui.inpDistMin.value() == 0
    assert log_dialog.ui.tableLogs.rowCount() == 1


def test_session_change_triggers_load(log_dialog, mock_log_service, qtbot):
    """Тест зміни сесії в ComboBox."""
    # Очищуємо дані
    log_dialog.all_entries = []

    # Додаємо нову сесію
    log_dialog.ui.cmbSessions.addItem("New Session", "new.jsonl")
    log_dialog.ui.cmbSessions.setCurrentIndex(1)

    # Перевіряємо, що дані завантажились (LogService.load_session_data повертає 1 елемент у моку)
    assert len(log_dialog.all_entries) == 1


def test_background_navigation_visibility(log_dialog):
    """Тест видимості контролів фону залежно від типу графіка."""
    log_dialog.ui.tabWidget.setCurrentIndex(2)  # Об'єкт

    # Режим "Шлях" (Path) - контроль фону має бути прихований
    log_dialog.ui.cmbTargetType.setCurrentIndex(0)
    assert log_dialog.ui.grpBackgroundControl.isHidden() is True

    # Режим "Спектр" (Spectrum) - має бути видимий
    # Спочатку виберемо об'єкт, щоб логіка спрацювала
    if log_dialog.ui.cmbTargetObject.count() > 0:
        log_dialog.ui.cmbTargetObject.setCurrentIndex(0)
        log_dialog.ui.cmbTargetType.setCurrentIndex(2)
        assert log_dialog.ui.grpBackgroundControl.isHidden() is False
