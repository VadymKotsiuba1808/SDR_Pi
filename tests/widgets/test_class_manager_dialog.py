"""
Тести для діалогу керування класами об'єктів (ClassManagerDialog).
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, ServiceResponse, StatusCode
from app.widgets.class_manager_dialog import ClassManagerDialog


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
def class_manager(qtbot, mock_network, mock_settings, mock_keyboard):
    """Фікстура для ініціалізації ClassManagerDialog."""
    dialog = ClassManagerDialog(mock_network, mock_settings, mock_keyboard)
    qtbot.addWidget(dialog)
    yield dialog
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.removeTranslator(dialog.translator)


def test_initial_load_request(qtbot, mock_network, mock_settings, mock_keyboard):
    """Тест того, що діалог при старті запитує список класів."""
    with patch(
        "app.widgets.class_manager_dialog.ClassManagerDialog._refresh_list"
    ) as mock_refresh:
        dialog = ClassManagerDialog(mock_network, mock_settings, mock_keyboard)
        qtbot.addWidget(dialog)
        assert mock_refresh.called


def test_populate_list_on_response(class_manager, mock_network):
    """Тест наповнення списку після відповіді від БД."""
    classes = [{"id": 1, "name": "Drone"}, {"id": 2, "name": "Bird"}]
    response = ServiceResponse(
        operation=DbOperation.GET_CLASSES,
        status=StatusCode.OK,
        message="Success",
        data={"classes": classes},
    )

    # Імітуємо відповідь мережі
    class_manager._handle_db_status(response)

    assert class_manager.ui.lstClasses.count() == 2
    assert class_manager.ui.lstClasses.item(0).text() == "Bird"  # Сортування за назвою
    assert class_manager.ui.lstClasses.item(1).text() == "Drone"


def test_add_class_request(class_manager, mock_network, qtbot):
    """Тест відправки запиту на додавання нового класу."""
    class_manager.ui.inpClassName.setText("NewClass")

    qtbot.mouseClick(class_manager.ui.btnAdd, Qt.MouseButton.LeftButton)

    # Перевіряємо, що викликано метод сервісу
    assert mock_network.request_db_add_class.called
    args = mock_network.request_db_add_class.call_args[0][0]
    assert isinstance(args, ObjectClass)
    assert args.name == "NewClass"


def test_add_class_success_update_ui(class_manager, qtbot):
    """Тест оновлення UI після успішного додавання класу."""
    class_manager.cached_classes = []

    response = ServiceResponse(
        operation=DbOperation.ADD_CLASS,
        status=StatusCode.CREATED,
        message="Created",
        data={"id": 10, "name": "AddedClass"},
    )

    class_manager._handle_db_status(response)

    assert class_manager.ui.lstClasses.count() == 1
    assert class_manager.ui.lstClasses.item(0).text() == "AddedClass"


def test_delete_class_request(class_manager, mock_network, qtbot):
    """Тест запиту на видалення класу."""
    # Додаємо клас в кеш та список
    cls = ObjectClass(id=5, name="To Delete")
    class_manager._populate_list([cls])

    # Обираємо елемент
    item = class_manager.ui.lstClasses.item(0)
    class_manager.ui.lstClasses.setCurrentItem(item)

    # Мокаємо QMessageBox для підтвердження
    with patch(
        "PyQt6.QtWidgets.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        qtbot.mouseClick(class_manager.ui.btnDelete, Qt.MouseButton.LeftButton)

    mock_network.request_db_delete_class.assert_called_once_with(5)


def test_rename_class_request(class_manager, mock_network, qtbot):
    """Тест запиту на перейменування існуючого класу."""
    cls = ObjectClass(id=1, name="OldName")
    class_manager._populate_list([cls])

    # Клікаємо на елемент для вибору (імітуємо вибір)
    item = class_manager.ui.lstClasses.item(0)
    class_manager.ui.lstClasses.setCurrentItem(item)
    class_manager._on_item_clicked(
        item
    )  # Встановлює текст в поле і змінює кнопку на "Save"

    class_manager.ui.inpClassName.setText("NewName")

    qtbot.mouseClick(class_manager.ui.btnAdd, Qt.MouseButton.LeftButton)

    assert mock_network.request_db_rename_class.called
    old_c, new_c = mock_network.request_db_rename_class.call_args[0]
    assert old_c.name == "OldName"
    assert new_c.name == "NewName"
    assert new_c.id == 1
