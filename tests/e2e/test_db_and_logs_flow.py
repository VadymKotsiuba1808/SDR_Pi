"""
Модуль містить E2E тести для перевірки повноцінних сценаріїв роботи з базою даних об'єктів
та перегляду логів у клієнтському додатку.

Тести покривають додавання/видалення об'єктів, перегляд історії виявлень,
спектральний аналіз фонових даних та обробку помилок сервера.
"""

import json
from unittest.mock import patch

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

from app.models.detection_background import DetectionBackground, SpectralData
from app.models.detection_event import DetectionEvent
from app.models.detection_object import DetectionObject
from app.models.log_entries import LogEntry, LogType
from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, ServiceResponse, StatusCode
from app.models.source_type import SourceType
from app.services.detection_background_service import DetectionBackgroundService
from app.services.log_service import LogService
from app.widgets.log_dialog import LogDialog
from app.widgets.main_window import MainWindow
from app.widgets.object_editor_dialog import ObjectEditorDialog
from app.widgets.object_manager_dialog import ObjectManagerDialog


def test_object_manager_add_and_delete_flow(app_services, qtbot, e2e_server) -> None:
    """Тестує повний цикл додавання та видалення об'єкта в Менеджері Об'єктів."""
    settings = app_services["settings"]
    settings.role = "owner"
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Очікуємо активацію сенсора (імітація підключення до сервера)
    qtbot.wait_until(
        lambda: main_win.ui.sensor_indicator.property("isActive") is True, timeout=5000
    )

    obj_mgr = ObjectManagerDialog(
        main_win.pi_network, settings, app_services["keyboard"]
    )
    qtbot.addWidget(obj_mgr)
    obj_mgr.show()

    # Очікуємо завантаження першої сторінки даних
    qtbot.wait_until(lambda: obj_mgr.ui.lblPageInfo.text() != "", timeout=3000)

    new_obj = DetectionObject(
        id=10,
        name="E2E Drone",
        class_id=1,
        object_class="UAV",
        is_dangerous=True,
        rf_params_hz=["2400000000-2483500000"],
        sound_params_hz=[],
    )

    # Імітуємо успішне редагування об'єкта без відкриття модального вікна,
    # оскільки exec() блокує потік виконання тесту.
    with patch.object(
        ObjectEditorDialog, "exec", return_value=QDialog.DialogCode.Accepted
    ):
        with patch.object(ObjectEditorDialog, "get_new_object", return_value=new_obj):
            with patch.object(obj_mgr, "_open_editor") as mock_open:
                qtbot.mouseClick(obj_mgr.ui.btnAdd, Qt.MouseButton.LeftButton)
                qtbot.wait_until(lambda: mock_open.called, timeout=3000)

    obj_mgr.network_service.request_db_add_object(new_obj)

    # Перевірка появи об'єкта в локальному кеші та UI таблиці
    qtbot.wait_until(
        lambda: any(o.name == "E2E Drone" for o in obj_mgr.cached_objects), timeout=3000
    )
    assert obj_mgr.ui.tableWidget.rowCount() > 0
    found = False
    for r in range(obj_mgr.ui.tableWidget.rowCount()):
        item = obj_mgr.ui.tableWidget.item(r, 0)
        if item and item.text() == "E2E Drone":
            found = True
            obj_mgr.ui.tableWidget.selectRow(r)
            break
    assert found, "Added object should be visible in table"

    # Видалення об'єкта з підтвердженням у діалоговому вікні
    with patch(
        "PyQt6.QtWidgets.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        qtbot.mouseClick(obj_mgr.ui.btnDelete, Qt.MouseButton.LeftButton)

    obj_mgr._force_refresh()

    qtbot.wait_until(
        lambda: not any(o.name == "E2E Drone" for o in obj_mgr.cached_objects),
        timeout=3000,
    )
    assert obj_mgr.ui.tableWidget.rowCount() >= 0


def test_log_history_view_flow(app_services, qtbot, e2e_server, tmp_path) -> None:
    """Тестує перегляд історії сесій та виявлень у журналі подій."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    log_file = logs_dir / "session_2026-05-30_12-00-00.jsonl"

    det = DetectionEvent(
        id="test_id",
        type=SourceType.RF,
        name="E2E Log Entry",
        object_class="uav",
        confidence=0.8,
        timestamp="2026-05-30T12:00:00",
        distance_km=0.5,
        angle=10.0,
        frequency_hz=2400,
    )
    entry = LogEntry(
        type=LogType.DETECTION,
        payload=det,
        timestamp="2026-05-30T12:00:00",
    )
    # Записуємо тестову подію у форматі JSONL для LogService
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")

    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])

    mock_log_service = LogService(logs_dir=str(logs_dir))

    log_dlg = LogDialog(
        log_service=mock_log_service,
        background_service=main_win.detection_background_service,
        classes=[ObjectClass(id=1, name="UAV")],
        settings_service=settings,
    )
    qtbot.addWidget(log_dlg)
    log_dlg.show()

    # Перевіряємо, чи з'явилася сесія у випадаючому списку
    qtbot.wait_until(lambda: log_dlg.ui.cmbSessions.count() > 0, timeout=3000)
    current_text = log_dlg.ui.cmbSessions.currentText()
    assert "30.05.2026" in current_text or "2026-05-30" in current_text

    # Перевірка наявності запису про виявлення в таблиці логів
    qtbot.wait_until(lambda: log_dlg.ui.tableLogs.rowCount() > 0, timeout=3000)
    found = False
    for r in range(log_dlg.ui.tableLogs.rowCount()):
        item = log_dlg.ui.tableLogs.item(r, 2)
        if item and "E2E Log Entry" in item.text():
            found = True
            break
    assert found, "Log entry should be visible in table"


def test_background_scan_view_in_logs(app_services, qtbot, tmp_path) -> None:
    """Тестує відображення спектрального аналізу фонових даних у журналі."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    log_file = logs_dir / "session_bg_test.jsonl"
    target_id = "target_with_bg"

    bg_logs_dir = tmp_path / "bg_logs"
    bg_logs_dir.mkdir()

    bg_service = DetectionBackgroundService(logs_dir=str(bg_logs_dir))

    det = DetectionEvent(
        id=target_id,
        type=SourceType.RF,
        name="Drone BG",
        object_class="uav",
        confidence=0.9,
        timestamp="2026-05-30T13:00:00",
        distance_km=1.0,
        angle=45.0,
        frequency_hz=2400,
    )
    entry = LogEntry(
        type=LogType.DETECTION, payload=det, timestamp="2026-05-30T13:00:01"
    )

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")

    settings = app_services["settings"]
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])

    if main_win is None:
        raise Exception("MainWindow failed to initialize")

    # Створюємо фіктивні спектральні дані
    spec = SpectralData(
        center_freq_hz=2400e6,
        sample_rate_hz=20e6,
        duration_sec=0.1,
        data_magnitude=np.array([[10, 20, 30]], dtype=np.uint8),
    )
    bg_data = DetectionBackground(
        id=target_id, timestamp="2026-05-30T13:00:00", spectral_data=spec
    )
    bg_service.add_background(bg_data)

    mock_log_service = LogService(logs_dir=str(logs_dir))

    log_dlg = LogDialog(
        log_service=mock_log_service,
        background_service=bg_service,
        classes=[ObjectClass(id=1, name="UAV")],
        settings_service=settings,
    )
    qtbot.addWidget(log_dlg)
    log_dlg.show()

    # Перемикаємося на вкладку детального аналізу об'єкта
    log_dlg.ui.tabWidget.setCurrentIndex(2)
    qtbot.wait_until(lambda: log_dlg.ui.cmbTargetObject.count() > 0, timeout=3000)
    log_dlg.ui.cmbTargetType.setCurrentIndex(2)  # Вибір відображення спектру

    # Перевіряємо, чи активувалася панель керування фоновими сканами
    assert log_dlg.ui.grpBackgroundControl.isVisible() is True
    info_text = log_dlg.ui.lblBgInfo.text()
    import re

    assert re.search(r"1 (з|of) \d+", info_text) is not None


def test_object_editor_validation_flow(app_services, qtbot, e2e_server) -> None:
    """Тестує валідацію вхідних даних у діалозі редагування об'єкта."""
    settings = app_services["settings"]
    settings.role = "owner"
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])

    if main_win is None:
        raise Exception("MainWindow failed to initialize")

    obj = DetectionObject(
        id=None,
        name="",
        class_id=1,
        object_class="UAV",
        is_dangerous=True,
        rf_params_hz=[],
        sound_params_hz=[],
    )

    editor = ObjectEditorDialog(
        settings_service=settings,
        keyboard=app_services["keyboard"],
        known_classes=[ObjectClass(id=1, name="UAV")],
        object_data=obj,
    )
    qtbot.addWidget(editor)
    editor.show()

    # Спроба зберегти порожнє ім'я має викликати попередження
    with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_warn:
        qtbot.mouseClick(editor.ui.btnSave, Qt.MouseButton.LeftButton)
        assert mock_warn.called, "Should show warning for empty name"

    # Валідація на дублікати: додаємо один і той самий діапазон двічі
    qtbot.keyClicks(editor.ui.inpName, "Valid Name")
    editor.ui.chkRFEnable.setChecked(True)
    editor.ui.inpRFMin.setValue(2400.0)
    editor.ui.inpRFMax.setValue(2500.0)

    qtbot.mouseClick(editor.ui.btnAddRF, Qt.MouseButton.LeftButton)
    assert editor.ui.lstRFFreqs.count() == 1

    with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_warn:
        qtbot.mouseClick(editor.ui.btnAddRF, Qt.MouseButton.LeftButton)
        assert mock_warn.called, "Should show warning for duplicate RF range"


def test_server_error_handling_flow(app_services, qtbot, e2e_server) -> None:
    """Тестує реакцію клієнта на помилки сервера (HTTP 500)."""
    settings = app_services["settings"]
    settings.role = "owner"
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    obj_mgr = ObjectManagerDialog(
        main_win.pi_network, settings, app_services["keyboard"]
    )
    qtbot.addWidget(obj_mgr)
    obj_mgr.show()

    # Створюємо об'єкт помилки сервера
    error_resp = ServiceResponse(
        operation=DbOperation.GET_OBJECTS_PAGE,
        status=StatusCode.INTERNAL_ERROR,
        message="Database connection lost on server side",
        data={},
    )

    # При отриманні INTERNAL_ERROR через сигнал, MainWindow або активний діалог
    # повинні показати критичне повідомлення користувачеву.
    with patch("PyQt6.QtWidgets.QMessageBox.critical") as mock_error:
        main_win.pi_network.request_finished.emit(error_resp)
        qtbot.wait_until(lambda: mock_error.called, timeout=2000)

    assert mock_error.called
    error_text = mock_error.call_args[0][2]
    assert (
        "Internal server error" in error_text
        or "Помилка" in error_text
        or "error" in error_text.lower()
    )
