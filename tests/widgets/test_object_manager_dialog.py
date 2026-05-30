"""
Тести для діалогу керування об'єктами (ObjectManagerDialog).
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

from app.models.detection_object import DetectionObject
from app.models.service_response import DbOperation, ServiceResponse, StatusCode
from app.widgets.object_manager_dialog import ObjectManagerDialog


@pytest.fixture
def mock_network():
    return MagicMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def mock_keyboard():
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def object_manager(qtbot, mock_network, mock_settings, mock_keyboard):
    """Фікстура для ініціалізації ObjectManagerDialog."""
    # Відключаємо початковий запит даних, щоб контролювати його в тестах
    with patch("app.widgets.object_manager_dialog.ObjectManagerDialog.refresh_data"):
        dialog = ObjectManagerDialog(mock_network, mock_settings, mock_keyboard)
        qtbot.addWidget(dialog)
        yield dialog
        from PyQt6.QtCore import QCoreApplication

        QCoreApplication.removeTranslator(dialog.translator)


def test_initialization_state(object_manager):
    """Тест початкового стану таблиці."""
    assert object_manager.ui.tableWidget.rowCount() == 0
    assert object_manager.current_page == 1


def test_populate_table_on_response(object_manager):
    """Тест наповнення таблиці після отримання сторінки даних."""
    items = [
        {
            "id": 1,
            "name": "Mavic",
            "object_class": "Drone",
            "is_dangerous": True,
            "rf_params_hz": ["2400-2483"],
            "sound_params_hz": [],
        }
    ]
    response = ServiceResponse(
        operation=DbOperation.GET_OBJECTS_PAGE,
        status=StatusCode.OK,
        message="Success",
        data={"items": items, "page": 1, "total": 1},
    )

    object_manager._handle_db_status(response)

    assert object_manager.ui.tableWidget.rowCount() == 1
    assert object_manager.ui.tableWidget.item(0, 0).text() == "Mavic"
    assert object_manager.ui.tableWidget.item(0, 1).text() == "Drone"
    # Перевірка кольору для небезпечного об'єкта
    assert (
        object_manager.ui.tableWidget.item(0, 2).foreground().color().name()
        == "#ff0000"
    )


def test_delete_object_request(object_manager, mock_network, qtbot):
    """Тест запиту на видалення об'єкта."""
    # Додаємо об'єкт в кеш і таблицю
    obj = DetectionObject(id=42, name="To Delete", object_class="test", class_id=1)
    object_manager._populate_table([obj])

    # Виділяємо рядок
    object_manager.ui.tableWidget.selectRow(0)

    with patch(
        "PyQt6.QtWidgets.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        qtbot.mouseClick(object_manager.ui.btnDelete, Qt.MouseButton.LeftButton)

    mock_network.request_db_delete_object.assert_called_once_with(42)


def test_open_add_dialog_flow(object_manager, mock_network, qtbot):
    """Тест ланцюжка відкриття діалогу додавання (спочатку запит класів)."""
    qtbot.mouseClick(object_manager.ui.btnAdd, Qt.MouseButton.LeftButton)

    # Повинен запитати класи
    mock_network.request_db_classes.assert_called_once()
    assert object_manager._waiting_classes_for_editor is True


def test_open_editor_on_classes_response(object_manager, qtbot):
    """Тест відкриття редактора після отримання списку класів."""
    object_manager._waiting_classes_for_editor = True

    response = ServiceResponse(
        operation=DbOperation.GET_CLASSES,
        status=StatusCode.OK,
        message="Success",
        data={"classes": [{"id": 1, "name": "Class1"}]},
    )

    with patch(
        "app.widgets.object_manager_dialog.ObjectEditorDialog.exec",
        return_value=QDialog.DialogCode.Rejected,
    ):
        object_manager._handle_db_status(response)

    assert object_manager._waiting_classes_for_editor is False


def test_pagination_logic(object_manager):
    """Тест логіки пагінації."""
    object_manager.total_pages = 3
    object_manager.current_page = 1
    object_manager._populate_table([])  # Оновить кнопки

    assert object_manager.ui.btnNextPage.isEnabled()
    assert not object_manager.ui.btnPrevPage.isEnabled()

    object_manager._next_page()
    assert object_manager.current_page == 2
