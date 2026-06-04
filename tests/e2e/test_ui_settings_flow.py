"""E2E тести для перевірки налаштувань користувацького інтерфейсу."""

import os
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog

from app.models.map_settings import CustomMapSettings
from app.widgets.main_window import MainWindow


def test_jammer_activation_and_timer_flow(app_services, qtbot, e2e_server) -> None:
    """Сценарій 8: Перевірка активації джаммера та відправки команд на сервер."""
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Очікуємо готовності GUI, що сигналізується активацією сенсора
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    e2e_server._handle_hardware_command = MagicMock()

    # Ініціюємо активацію джаммера через інтерфейс користувача
    qtbot.mouseClick(main_win.ui.jammerOnTimerButton, Qt.MouseButton.LeftButton)

    assert main_win.jammer_service.is_active is True
    # Чекаємо на асинхронне завершення мережевого запиту до сервера
    qtbot.wait_until(lambda: e2e_server._handle_hardware_command.called, timeout=2000)
    assert e2e_server._handle_hardware_command.call_args_list[0][0][0] == "start_alarm"

    # Деактивація джаммера та перевірка скидання стану
    qtbot.mouseClick(main_win.ui.jammerOffTimerButton, Qt.MouseButton.LeftButton)
    assert main_win.jammer_service.is_active is False

    def check_stop_alarm() -> bool:
        """Перевірка наявності команди зупинки тривоги в списку викликів."""
        calls = [c[0][0] for c in e2e_server._handle_hardware_command.call_args_list]
        return "stop_alarm" in calls

    qtbot.wait_until(check_stop_alarm, timeout=3000)


def test_wifi_indicator_updates(app_services, qtbot) -> None:
    """Сценарій 9: Перевірка динамічного оновлення рівня сигналу WiFi."""
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Імітуємо високий рівень сигналу для перевірки відображення 3-х поділок
    with patch.object(
        main_win.network_signal_service, "get_signal_strength", return_value=75
    ):
        main_win.update_wifi_signal_info()
        assert main_win.ui.WiFi_level.property("level") == 3

    # Імітуємо слабкий сигнал для перевірки перемикання на 1 поділку
    with patch.object(
        main_win.network_signal_service, "get_signal_strength", return_value=10
    ):
        main_win.update_wifi_signal_info()
        assert main_win.ui.WiFi_level.property("level") == 1


def test_custom_map_setup_flow(app_services, qtbot, e2e_server) -> None:
    """Сценарій 15: Валідація процесу встановлення кастомної растрової мапи."""
    settings = app_services["settings"]
    # Для доступу до функцій адміністрування мап потрібні права власника
    settings.role = "owner"
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    test_map_path = os.path.abspath("test_data/map.jpg")

    # Мокуємо діалоги, щоб уникнути блокування головного потоку GUI
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

        # Переконуємося, що дані з діалогу були успішно інтегровані в стан головного вікна
        assert main_win.custom_map_settings == fake_settings
        assert main_win.current_map is not None


def test_ui_localization_and_units_flow(app_services, qtbot) -> None:
    """Сценарій 16: Перевірка механізму зміни мови інтерфейсу."""
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    initial_idx = main_win.ui.langComboBox.currentIndex()
    target_idx = 1 if initial_idx == 0 else 0

    # Патчимо метод завантаження, щоб перевірити факт його виклику без реальної зміни мови процесу
    with patch.object(MainWindow, "load_language") as mock_load:
        main_win.ui.langComboBox.setCurrentIndex(target_idx)

        # Перевірка відповідності індексу ComboBox коду мови в налаштуваннях
        expected_lang = "en" if target_idx == 1 else "uk"
        assert settings.lang_code == expected_lang
        assert mock_load.called
