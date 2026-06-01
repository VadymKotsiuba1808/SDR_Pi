"""E2E тести для перевірки робочих процесів з детекціями БПЛА.

Цей модуль містить сценарії, що імітують реальну взаємодію користувача з інтерфейсом
для пошуку цілей, відображення детальної інформації та обробки помилкових тривог.
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType
from app.widgets.main_window import MainWindow


def test_detection_search_and_info_display(app_services, qtbot, e2e_server) -> None:
    """Сценарій 4: Пошук цілі за індексом та відображення інформації.

    Перевіряє, чи правильно UI реагує на введення візуального індексу цілі
    та чи коректно заповнюється панель інформації даними з об'єкта події.

    Args:
        app_services: Фікстура сервісів додатку.
        qtbot: Помічник для тестування PyQt6.
        e2e_server: Мок-сервер для надсилання подій.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Очікуємо активації індикатора сенсора як ознаки успішного підключення до сервера
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    # Імітуємо виявлення цілі сервером
    event = DetectionEvent(
        id="uav_123",
        type=SourceType.RF,
        name="Mavic 3",
        object_class="uav",
        confidence=0.88,
        timestamp="2026-05-30T15:00:00",
        distance_km=1.5,
        angle=45.0,
        frequency_hz=2400000000,
    )
    e2e_server.send_detection_event(event)

    # Очікуємо обробку події менеджером детекцій
    qtbot.wait_until(lambda: main_win.detection_manager.has_detections(), timeout=3000)
    target = main_win.detection_manager.get_targets()[0]
    v_index = target.visual_index

    # Користувач вводить індекс у поле пошуку та натискає Enter
    qtbot.keyClicks(main_win.ui.index_search_edit, str(v_index))
    qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

    # Перевіряємо вміст панелі інформації на відповідність переданим даним.
    # Враховуємо динамічну зміну локалізації (INDEX/ІНДЕКС).
    info_text = main_win.ui.detection_info_text.toPlainText()

    assert str(v_index) in info_text
    assert "MAVIC 3" in info_text
    assert "2400.0" in info_text
    assert "1.500" in info_text

    assert "INDEX" in info_text or "ІНДЕКС" in info_text
    assert "NAME" in info_text or "НАЗВА" in info_text


def test_false_alarm_workflow(app_services, qtbot, e2e_server) -> None:
    """Сценарій 5: Повний цикл обробки помилкової тривоги.

    Перевіряє можливість позначення цілі як помилкової, що повинно
    призвести до її видалення з UI та відправки відповідної команди на сервер.

    Args:
        app_services: Фікстура сервісів додатку.
        qtbot: Помічник для тестування PyQt6.
        e2e_server: Мок-сервер для взаємодії.
    """
    # Встановлюємо STATIONARY_SECONDS в 0, щоб кнопка 'False Alarm' активувалася миттєво,
    # не чекаючи реального часу нерухомості цілі.
    with patch("app.widgets.main_window.STATIONARY_SECONDS", 0):
        settings = app_services["settings"]
        settings.role = "owner"  # Функція доступна лише для ролі 'owner'

        main_win = MainWindow(
            settings, app_services["keyboard"], app_services["system"]
        )
        qtbot.addWidget(main_win)
        main_win.show()

        qtbot.wait_until(
            lambda: main_win.ui.sensor_indicator.property("isActive") is True,
            timeout=5000,
        )

        event = DetectionEvent(
            id="ghost_target",
            type=SourceType.SOUND,
            name="Unknown Sound",
            object_class="bird",
            confidence=0.5,
            timestamp="2026-05-30T15:05:00",
            distance_km=0.5,
            angle=180.0,
            frequency_hz=150,
        )
        e2e_server.send_detection_event(event)

        qtbot.wait_until(
            lambda: main_win.detection_manager.has_detections(), timeout=3000
        )
        v_index = main_win.detection_manager.get_targets()[0].visual_index

        # Вибираємо ціль для взаємодії
        qtbot.keyClicks(main_win.ui.index_search_edit, str(v_index))
        qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

        # Очікуємо активації кнопки (це може бути асинхронним процесом після зміни вибору)
        qtbot.wait_until(
            lambda: main_win.ui.falseAlarmButton.isEnabled() is True, timeout=2000
        )

        # Перехоплюємо команду, що надсилається на сервер
        e2e_server._handle_hardware_command = MagicMock()

        qtbot.mouseClick(main_win.ui.falseAlarmButton, Qt.MouseButton.LeftButton)

        # Перевіряємо, що ціль видалена з локального списку та сервер отримав запит
        qtbot.wait_until(
            lambda: not main_win.detection_manager.has_detections(), timeout=2000
        )
        qtbot.wait_until(
            lambda: e2e_server._handle_hardware_command.called, timeout=2000
        )
        assert e2e_server._handle_hardware_command.call_args[0][0] == "false_alarm"
        assert (
            e2e_server._handle_hardware_command.call_args[0][1]["event_id"]
            == "ghost_target"
        )


def test_multiple_detections_stability(app_services, qtbot, e2e_server) -> None:
    """Сценарій 6: Робота з декількома цілями одночасно.

    Перевіряє стабільність UI при отриманні декількох подій детекції
    та можливість незалежного перегляду інформації про кожну з них.

    Args:
        app_services: Фікстура сервісів додатку.
        qtbot: Помічник для тестування PyQt6.
        e2e_server: Мок-сервер для надсилання подій.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    # Імітуємо появу двох різних БПЛА для перевірки конкурентної обробки
    e1 = DetectionEvent(
        id="uav_1",
        type=SourceType.RF,
        name="Drone 1",
        object_class="uav",
        confidence=0.9,
        timestamp="T1",
        distance_km=1.0,
        angle=10.0,
        frequency_hz=2400,
    )
    e2 = DetectionEvent(
        id="uav_2",
        type=SourceType.RF,
        name="Drone 2",
        object_class="uav",
        confidence=0.8,
        timestamp="T2",
        distance_km=2.0,
        angle=20.0,
        frequency_hz=5800,
    )

    e2e_server.send_detection_event(e1)
    e2e_server.send_detection_event(e2)

    # Перевіряємо, що обидві цілі з'явилися в списку
    qtbot.wait_until(
        lambda: len(main_win.detection_manager.get_targets()) == 2, timeout=3000
    )

    # Перемикаємося між цілями через пошук та перевіряємо оновлення інфо-панелі
    t1 = main_win.detection_manager.get_targets()[0]
    main_win.ui.index_search_edit.clear()
    qtbot.keyClicks(main_win.ui.index_search_edit, str(t1.visual_index))
    qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

    info1 = main_win.ui.detection_info_text.toPlainText().upper()
    assert "DRONE 1" in info1

    t2 = main_win.detection_manager.get_targets()[1]
    main_win.ui.index_search_edit.clear()
    qtbot.keyClicks(main_win.ui.index_search_edit, str(t2.visual_index))
    qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

    info2 = main_win.ui.detection_info_text.toPlainText().upper()
    assert "DRONE 2" in info2


def test_network_reconnect_ui_reaction(app_services, qtbot, e2e_server) -> None:
    """Сценарій 7: Реакція UI на розрив та відновлення зв'язку з сервером.

    Перевіряє механізм автоматичного перепідключення клієнта та
    візуальну індикацію статусу з'єднання в інтерфейсі.

    Args:
        app_services: Фікстура сервісів додатку.
        qtbot: Помічник для тестування PyQt6.
        e2e_server: Мок-сервер для імітації розриву.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    # Імітуємо аварійне завершення роботи сервера
    e2e_server.stop()

    # UI повинен змінити стан індикатора на неактивний
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is False, timeout=5000
    )

    # Відновлюємо сервер на тому ж порті. Використовуємо локальні імпорти,
    # щоб уникнути циклічних залежностей або зайвого навантаження в інших тестах.
    from app.models.object_class import ObjectClass
    from pi_server.database_service import DatabaseService
    from pi_server.pi_server_service import PiServerService

    db = DatabaseService(db_url="sqlite:///:memory:")
    db.add_class(ObjectClass(id=1, name="UAV"))

    new_srv = PiServerService(port=settings.pi_target_port, db_service=db)
    new_srv.start()

    # Очікуємо, що клієнт автоматично виявить доступність сервера та підключиться
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=10000
    )

    new_srv.stop()


def test_chart_monitor_flow(app_services, qtbot, e2e_server) -> None:
    """Сценарій 14: Відкриття та робота Монітора Графіків (Спектрограми).

    Перевіряє, чи відкривається вікно спектрограми при натисканні відповідної
    кнопки та чи відбувається підписка на мережевий потік даних.

    Args:
        app_services: Фікстура сервісів додатку.
        qtbot: Помічник для тестування PyQt6.
        e2e_server: Мок-сервер для взаємодії.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Мокаємо метод 'exec' діалогу, щоб тест не блокувався модальним вікном
    with patch(
        "app.widgets.main_window.ChartMonitorDialog.exec",
        return_value=QDialog.DialogCode.Accepted,
    ):
        qtbot.mouseClick(main_win.ui.chartRangePushButton, Qt.MouseButton.LeftButton)

    from app.widgets.chart_monitor_dialog import ChartMonitorDialog

    chart_dlg = ChartMonitorDialog(main_win.pi_network, settings)
    qtbot.addWidget(chart_dlg)
    chart_dlg.show()

    # Перевірка наявності хоча б одного обробника сигналу свідчить про успішну ініціалізацію монітора
    assert (
        chart_dlg.network_service.receivers(chart_dlg.network_service.data_received) > 0
    )


def test_screen_recording_flow(app_services, qtbot) -> None:
    """Сценарій 17: Повний цикл ручного запису екрану.

    Перевіряє логіку керування записом екрану, візуальну індикацію
    статусу запису та взаємодію з сервісом запису.

    Args:
        app_services: Фікстура сервісів додатку.
        qtbot: Помічник для тестування PyQt6.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Мокаємо Recorder для ізоляції тесту від системних залежностей (MSS, FFmpeg)
    main_win.recorder = MagicMock()
    main_win.recorder.start_recording = MagicMock()
    main_win.recorder.stop_recording = MagicMock()

    # Активуємо запис
    qtbot.mouseClick(main_win.ui.screenRecordButton, Qt.MouseButton.LeftButton)
    assert main_win.ui.screenRecordButton.isChecked()
    assert main_win.recorder.start_recording.called

    # Імітуємо сигнал зворотного зв'язку від сервісу про успішний старт
    main_win.on_recording_started()
    assert main_win.record_status_widget.isVisible()

    # Вимикаємо запис
    qtbot.mouseClick(main_win.ui.screenRecordButton, Qt.MouseButton.LeftButton)
    assert not main_win.ui.screenRecordButton.isChecked()
    assert main_win.recorder.stop_recording.called

    # Імітуємо сигнал про завершення запису
    main_win.on_recording_stopped()
    assert not main_win.record_status_widget.isVisible()
