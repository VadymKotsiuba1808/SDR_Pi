"""
E2E тести для перевірки налаштувань UI, мап та керування обладнанням.
Охоплює встановлення кастомних мап та роботу з джаммером.
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from app.widgets.main_window import MainWindow


def test_jammer_activation_and_timer_flow(app_services, qtbot, e2e_server):
    """
    Сценарій 8: Активація джаммера та перевірка таймера/команд.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    e2e_server._handle_hardware_command = MagicMock()

    # 1. Натискаємо кнопку ввімкнення "Глушилки"
    qtbot.mouseClick(main_win.ui.jammerOnTimerButton, Qt.MouseButton.LeftButton)

    # 2. Перевірка:
    assert main_win.jammer_service.is_active is True
    qtbot.wait_until(lambda: e2e_server._handle_hardware_command.called, timeout=2000)
    assert e2e_server._handle_hardware_command.call_args_list[0][0][0] == "start_alarm"

    # 3. Вимикаємо
    qtbot.mouseClick(main_win.ui.jammerOffTimerButton, Qt.MouseButton.LeftButton)
    assert main_win.jammer_service.is_active is False

    def check_stop_alarm():
        calls = [c[0][0] for c in e2e_server._handle_hardware_command.call_args_list]
        return "stop_alarm" in calls

    qtbot.wait_until(check_stop_alarm, timeout=3000)


def test_wifi_indicator_updates(app_services, qtbot):
    """
    Сценарій 9: Оновлення індикатора WiFi при зміні рівня сигналу.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    with patch.object(
        main_win.network_signal_service, "get_signal_strength", return_value=75
    ):
        main_win.update_wifi_signal_info()
        assert main_win.ui.WiFi_level.property("level") == 3

    with patch.object(
        main_win.network_signal_service, "get_signal_strength", return_value=10
    ):
        main_win.update_wifi_signal_info()
        assert main_win.ui.WiFi_level.property("level") == 1


def test_custom_map_setup_flow(app_services, qtbot, e2e_server):
    """
    Сценарій 15: Встановлення кастомної мапи через діалогове вікно.
    """
    settings = app_services["settings"]
    settings.role = "owner"
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # 1. Емулюємо натискання кнопки "Додати карту"
    import os

    test_map_path = os.path.abspath("test_data/map.jpg")

    with (
        patch(
            "app.widgets.main_window.SetMapDialog.exec",
            return_value=QDialog.DialogCode.Accepted,
        ),
        patch(
            "app.widgets.set_map_dialog.QFileDialog.getOpenFileName",
            return_value=(test_map_path, "Images (*.jpg)"),
        ),
        patch("app.widgets.main_window.SetMapDialog.get_settings") as mock_get_settings,
    ):
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QPixmap

        from app.models.map_settings import CustomMapSettings

        mock_pixmap = QPixmap(100, 100)
        mock_pixmap.fill(Qt.GlobalColor.red)

        fake_settings = CustomMapSettings(
            pixmap=mock_pixmap,
            px_per_km=100.0,
            rotation=0.0,
            total_diameter_km=1.0,
            center_px_point=QPoint(50, 50),
        )
        mock_get_settings.return_value = fake_settings

        qtbot.mouseClick(main_win.ui.addMapButton, Qt.MouseButton.LeftButton)

        assert main_win.custom_map_settings == fake_settings
        assert main_win.current_map is not None


def test_ui_localization_and_units_flow(app_services, qtbot):
    """
    Сценарій 16: Зміна мови та перевірка оновлення UI.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    initial_idx = main_win.ui.langComboBox.currentIndex()
    target_idx = 1 if initial_idx == 0 else 0

    with patch.object(MainWindow, "load_language") as mock_load:
        main_win.ui.langComboBox.setCurrentIndex(target_idx)
        assert settings.lang_code == ("en" if target_idx == 1 else "uk")
        assert mock_load.called
