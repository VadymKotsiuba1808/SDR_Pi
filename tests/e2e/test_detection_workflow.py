"""
E2E тести для перевірки робочих процесів з детекціями БПЛА.
Охоплює пошук цілей, відображення інформації та обробку помилкових тривог.
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType
from app.widgets.main_window import MainWindow


def test_detection_search_and_info_display(app_services, qtbot, e2e_server):
    """
    Сценарій 4: Пошук цілі за індексом та відображення інформації.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # 1. Чекаємо коннекту
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    # 2. Сервер надсилає детекцію
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

    # 3. Чекаємо появи цілі в менеджері (вона отримає візуальний індекс, зазвичай 1)
    qtbot.wait_until(lambda: main_win.detection_manager.has_detections(), timeout=3000)
    target = main_win.detection_manager.get_targets()[0]
    v_index = target.visual_index

    # 4. Вводимо індекс у поле пошуку
    qtbot.keyClicks(main_win.ui.index_search_edit, str(v_index))
    qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

    # 5. Перевіряємо інфо-панель (враховуємо локалізацію)
    info_text = main_win.ui.detection_info_text.toPlainText()

    # Перевіряємо наявність значень, а не міток
    assert str(v_index) in info_text
    assert "MAVIC 3" in info_text
    assert "2400.0" in info_text
    assert "1.500" in info_text

    # Перевіряємо, що хоча б одна з міток (Eng/Ukr) присутня
    assert "INDEX" in info_text or "ІНДЕКС" in info_text
    assert "NAME" in info_text or "НАЗВА" in info_text


def test_false_alarm_workflow(app_services, qtbot, e2e_server):
    """
    Сценарій 5: Повний цикл обробки помилкової тривоги.
    """
    # Зменшуємо час очікування "нерухомості" для тесту
    with patch("app.widgets.main_window.STATIONARY_SECONDS", 0):
        settings = app_services["settings"]
        settings.role = "owner"  # Тільки власник може звітувати про помилкові тривоги

        main_win = MainWindow(
            settings, app_services["keyboard"], app_services["system"]
        )
        qtbot.addWidget(main_win)
        main_win.show()

        qtbot.wait_until(
            lambda: main_win.ui.sensor_indicator.property("isActive") is True,
            timeout=5000,
        )

        # 1. Надсилаємо детекцію
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

        # 2. Вибираємо ціль (через пошук)
        qtbot.keyClicks(main_win.ui.index_search_edit, str(v_index))
        qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

        # 3. Перевіряємо, що кнопка False Alarm стала активною (завдяки STATIONARY_SECONDS=0)
        assert main_win.ui.falseAlarmButton.isEnabled() is True, (
            "False Alarm button should be enabled for stationary target"
        )

        # 4. Мокаємо метод обробки на сервері для перевірки отримання команди
        e2e_server._handle_hardware_command = MagicMock()

        # 5. Натискаємо "Помилкова тривога"
        qtbot.mouseClick(main_win.ui.falseAlarmButton, Qt.MouseButton.LeftButton)

        # 6. Перевірка:
        # а) Ціль зникла з менеджера
        qtbot.wait_until(
            lambda: not main_win.detection_manager.has_detections(), timeout=2000
        )
        # б) Команда пішла на сервер
        qtbot.wait_until(
            lambda: e2e_server._handle_hardware_command.called, timeout=2000
        )
        assert e2e_server._handle_hardware_command.call_args[0][0] == "false_alarm"
        assert (
            e2e_server._handle_hardware_command.call_args[0][1]["event_id"]
            == "ghost_target"
        )


def test_multiple_detections_stability(app_services, qtbot, e2e_server):
    """
    Сценарій 6: Робота з декількома цілями одночасно.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    # 1. Надсилаємо дві цілі
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

    qtbot.wait_until(
        lambda: len(main_win.detection_manager.get_targets()) == 2, timeout=3000
    )

    # 2. Вибираємо першу ціль
    t1 = main_win.detection_manager.get_targets()[0]
    main_win.ui.index_search_edit.clear()
    qtbot.keyClicks(main_win.ui.index_search_edit, str(t1.visual_index))
    qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

    # Текст у панелі може бути у верхньому регістрі
    info1 = main_win.ui.detection_info_text.toPlainText().upper()
    assert "DRONE 1" in info1

    # 3. Вибираємо другу ціль
    t2 = main_win.detection_manager.get_targets()[1]
    main_win.ui.index_search_edit.clear()
    qtbot.keyClicks(main_win.ui.index_search_edit, str(t2.visual_index))
    qtbot.keyClick(main_win.ui.index_search_edit, Qt.Key.Key_Enter)

    info2 = main_win.ui.detection_info_text.toPlainText().upper()
    assert "DRONE 2" in info2


def test_network_reconnect_ui_reaction(app_services, qtbot, e2e_server):
    """
    Сценарій 7: Реакція UI на розрив та відновлення зв'язку з сервером.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # 1. Чекаємо стабільного з'єднання
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    # 2. Зупиняємо сервер (розрив)
    e2e_server.stop()

    # Перевіряємо, що індикатор став неактивним
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is False, timeout=5000
    )

    # 3. Перезапускаємо сервер (відновлення)
    # Створюємо новий сервер на тому ж порту (settings.pi_target_port вже знає порт)
    from app.models.object_class import ObjectClass
    from pi_server.database_service import DatabaseService
    from pi_server.pi_server_service import PiServerService

    db = DatabaseService(db_url="sqlite:///:memory:")
    db.add_class(ObjectClass(id=1, name="UAV"))

    new_srv = PiServerService(port=settings.pi_target_port, db_service=db)
    new_srv.start()

    # Перевіряємо, що клієнт сам перепідключився
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=10000
    )

    new_srv.stop()


def test_chart_monitor_flow(app_services, qtbot, e2e_server):
    """
    Сценарій 14: Відкриття та робота Монітора Графіків (Спектрограми).
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    with patch(
        "app.widgets.main_window.ChartMonitorDialog.exec",
        return_value=QDialog.DialogCode.Accepted,
    ):
        qtbot.mouseClick(main_win.ui.chartRangePushButton, Qt.MouseButton.LeftButton)

    from app.widgets.chart_monitor_dialog import ChartMonitorDialog

    chart_dlg = ChartMonitorDialog(main_win.pi_network, settings)
    qtbot.addWidget(chart_dlg)
    chart_dlg.show()

    # Перевіряємо, що діалог підписався на дані
    assert (
        chart_dlg.network_service.receivers(chart_dlg.network_service.data_received) > 0
    )


def test_screen_recording_flow(app_services, qtbot):
    """
    Сценарій 17: Повний цикл ручного запису екрану.
    """
    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Мокаємо Recorder щоб не запускати MSS/FFmpeg в тестах
    main_win.recorder = MagicMock()
    # Імітуємо старт
    main_win.recorder.start_recording = MagicMock()
    main_win.recorder.stop_recording = MagicMock()

    # 1. Починаємо запис
    qtbot.mouseClick(main_win.ui.screenRecordButton, Qt.MouseButton.LeftButton)
    assert main_win.ui.screenRecordButton.isChecked()
    assert main_win.recorder.start_recording.called

    # Емулюємо сигнал від сервісу, що запис почався
    main_win.on_recording_started()
    assert main_win.record_status_widget.isVisible()

    # 2. Зупиняємо запис
    qtbot.mouseClick(main_win.ui.screenRecordButton, Qt.MouseButton.LeftButton)
    assert not main_win.ui.screenRecordButton.isChecked()
    assert main_win.recorder.stop_recording.called

    # Емулюємо сигнал від сервісу, що запис зупинився
    main_win.on_recording_stopped()
    assert not main_win.record_status_widget.isVisible()
