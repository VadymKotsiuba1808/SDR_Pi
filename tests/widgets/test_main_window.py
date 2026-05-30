"""
Комплексні тести для головного вікна (MainWindow).
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from app.models.detection_event import DetectionEvent
from app.models.gps_data import GPSData
from app.models.source_type import SourceType
from app.widgets.main_window import MainWindow


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.lang_code = "uk"
    settings.role = "owner"
    settings.radar_max_radius_km = 100.0
    settings.radar_radius_km = 5.0
    settings.radio_range_mhz = [400, 6000]
    settings.gps_interval_s = 60
    settings.is_jammer_auto_start_enabled = False
    return settings


@pytest.fixture
def mock_keyboard():
    return MagicMock()


@pytest.fixture
def mock_system():
    system = MagicMock()
    system.is_windows = True
    system.is_linux = False
    return system


@pytest.fixture
def main_window(qtbot, mock_settings, mock_keyboard, mock_system):
    """Фікстура для ініціалізації MainWindow з моками всіх сервісів."""

    # Налаштовуємо мок джаммера
    mock_jammer = patch("app.widgets.main_window.JammerService").start()
    mock_jammer.return_value.get_formatted_time.return_value = "00:00:00"

    # Решта сервісів
    patch("app.widgets.main_window.MapService").start()
    patch("app.widgets.main_window.PiNetworkService").start()
    patch("app.widgets.main_window.LogService").start()
    patch("app.widgets.main_window.RecordingService").start()
    patch("app.widgets.main_window.MediaPlayerService").start()
    patch("app.widgets.main_window.NetworkSignalService").start()
    patch("app.widgets.main_window.DetectionBackgroundService").start()
    patch("app.widgets.main_window.DetectionManager").start()

    with patch("app.widgets.main_window.QStorageInfo") as mock_storage:
        mock_storage.return_value.bytesAvailable.return_value = 10 * 1024 * 1024 * 1024

        window = MainWindow(mock_settings, mock_keyboard, mock_system)
        qtbot.addWidget(window)
        yield window

        # Зупиняємо таймери перед виходом, щоб вони не стріляли в інших тестах
        window.timer_1sec.stop()
        window.timer_radar.stop()
        window.timer_wifi.stop()
        window.timer_gps.stop()
        patch.stopall()


def test_initial_ui_state_owner(main_window, mock_settings):
    """Тест початкового стану UI для ролі Owner."""
    # Використовуємо isHidden() бо віджет може бути не 'visible' до реального відображення на екрані
    assert main_window.ui.falseAlarmButton.isHidden() is False
    assert main_window.ui.menuButton.isHidden() is False
    assert main_window.ui.backToLoginButton.isHidden() is True
    assert main_window.ui.radarRadiusSpinbox.value() == 5.0


def test_initial_ui_state_operator(qtbot, mock_settings, mock_keyboard, mock_system):
    """Тест UI для ролі Operator."""
    mock_settings.role = "operator"

    with (
        patch("app.widgets.main_window.MapService"),
        patch("app.widgets.main_window.PiNetworkService"),
        patch("app.widgets.main_window.LogService"),
        patch("app.widgets.main_window.DetectionManager"),
        patch("app.widgets.main_window.JammerService"),
        patch("app.widgets.main_window.RecordingService"),
        patch("app.widgets.main_window.MediaPlayerService"),
        patch("app.widgets.main_window.NetworkSignalService"),
        patch("app.widgets.main_window.DetectionBackgroundService"),
        patch("app.widgets.main_window.QStorageInfo") as mock_storage,
    ):
        mock_storage.return_value.bytesAvailable.return_value = 10 * 1024 * 1024 * 1024

        window = MainWindow(mock_settings, mock_keyboard, mock_system)
        qtbot.addWidget(window)

        assert window.ui.falseAlarmButton.isHidden() is True
        assert window.ui.menuButton.isHidden() is True
        assert window.ui.backToLoginButton.isHidden() is False


def test_change_language(main_window, mock_settings):
    """Тест перемикання мови."""
    # Перемикаємо на English (індекс 1)
    main_window.ui.langComboBox.setCurrentIndex(1)
    assert mock_settings.lang_code == "en"

    # Перемикаємо назад на Українську (індекс 0)
    main_window.ui.langComboBox.setCurrentIndex(0)
    assert mock_settings.lang_code == "uk"


def test_handle_gps_updates_coords(main_window, qtbot):
    """Тест оновлення координат при отриманні GPS."""
    new_gps = GPSData(lat=50.0, lon=30.0, strength=90)

    # Мокаємо refresh_map, щоб не робити реальних запитів
    with patch.object(main_window, "refresh_map") as mock_refresh:
        main_window.handle_gps(new_gps)

        assert main_window.current_coords == [50.0, 30.0]
        # Чекаємо виклику QTimer.singleShot(0, ...)
        qtbot.waitUntil(lambda: mock_refresh.called, timeout=1000)
        assert main_window.ui.GPS_level.property("level") == 4


def test_handle_detection_adds_to_manager_and_logs(main_window):
    """Тест обробки події детекції."""
    event = DetectionEvent(
        id="uav_1",
        type=SourceType.RF,
        name="Mavic",
        object_class="drone",
        confidence=0.9,
        timestamp="2026-05-30T12:00:00",
        distance_km=1.2,
        angle=10.0,
        frequency_hz=2.4e9,
    )

    main_window.handle_detection(event)

    # Перевіряємо виклики менеджерів
    main_window.detection_manager.add_detection.assert_called_once_with(event)
    main_window.log_service.add_log.assert_called_once()


def test_jammer_auto_start(main_window, mock_settings):
    """Тест автостарту глушилки при детекції."""
    mock_settings.is_jammer_auto_start_enabled = True
    main_window.jammer_service.is_active = False

    event = DetectionEvent(
        id="1",
        type=SourceType.RF,
        name="T",
        object_class="d",
        confidence=0.5,
        timestamp="2026-05-30T12:00:00",
        distance_km=1.0,
        angle=0.0,
        frequency_hz=915e6,
    )
    main_window.handle_detection(event)

    assert main_window.jammer_service.start.called


def test_toggle_recording(main_window, qtbot):
    """Тест запуску/зупинки запису екрану."""
    # 1. Починаємо запис
    main_window.recorder.is_running = False
    qtbot.mouseClick(main_window.ui.screenRecordButton, Qt.MouseButton.LeftButton)
    assert main_window.recorder.start_recording.called

    # 2. Зупиняємо запис
    main_window.recorder.is_running = True
    qtbot.mouseClick(main_window.ui.screenRecordButton, Qt.MouseButton.LeftButton)
    assert main_window.recorder.stop_recording.called


def test_alert_status_ui(main_window):
    """Тест відображення статусу тривоги в UI."""
    # Імітуємо наявність RF детекції
    mock_target = MagicMock()
    mock_target.event.type = SourceType.RF
    main_window.detection_manager.get_targets.return_value = [mock_target]

    main_window.update_alert_status()

    assert main_window.ui.RF_alert.property("alert") is True
    assert main_window.ui.Sound_alert.property("alert") is False


def test_open_settings_dialog(main_window, qtbot):
    """Тест відкриття діалогу налаштувань."""
    with patch(
        "app.widgets.main_window.SettingsDialog.exec",
        return_value=QDialog.DialogCode.Accepted,
    ):
        qtbot.mouseClick(main_window.ui.menuButton, Qt.MouseButton.LeftButton)
        # Якщо exec був викликаний, значить логіка спрацювала
