"""
Тести для діалогу редагування об'єктів.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.widgets.object_editor_dialog import ObjectEditorDialog


@pytest.fixture
def mock_settings():
    """Фікстура для макета налаштувань."""
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def mock_keyboard():
    """Фікстура для макета сервісу клавіатури."""
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def known_classes():
    """Фікстура для списку відомих класів."""
    return [
        ObjectClass(id=1, name="Drone"),
        ObjectClass(id=2, name="Bird"),
    ]


@pytest.fixture
def object_editor_add(qtbot, mock_settings, mock_keyboard, known_classes):
    """Фікстура для діалогу в режимі додавання."""
    dialog = ObjectEditorDialog(mock_settings, mock_keyboard, known_classes)
    qtbot.addWidget(dialog)
    yield dialog
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.removeTranslator(dialog.translator)


@pytest.fixture
def object_editor_edit(qtbot, mock_settings, mock_keyboard, known_classes):
    """Фікстура для діалогу в режимі редагування."""
    obj = DetectionObject(
        id=10,
        name="Existing Object",
        class_id=1,
        object_class="Drone",
        is_dangerous=True,
        rf_params_hz=["2400000000-2483500000"],
        sound_params_hz=[]
    )
    dialog = ObjectEditorDialog(mock_settings, mock_keyboard, known_classes, object_data=obj)
    qtbot.addWidget(dialog)
    yield dialog
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.removeTranslator(dialog.translator)


def test_add_mode_initial_state(object_editor_add):
    """Тест початкового стану в режимі додавання."""
    assert object_editor_add.ui.inpName.text() == ""
    assert object_editor_add.ui.comboClass.count() == 2
    assert object_editor_add.ui.chkRFEnable.isChecked() is True
    assert object_editor_add.ui.chkSoundEnable.isChecked() is False


def test_edit_mode_loading(object_editor_edit):
    """Тест завантаження даних в режимі редагування."""
    assert object_editor_edit.ui.inpName.text() == "Existing Object"
    assert object_editor_edit.ui.comboClass.currentText() == "Drone"
    assert object_editor_edit.ui.chkDangerous.isChecked() is True
    assert object_editor_edit.ui.lstRFFreqs.count() == 1


def test_toggle_rf_sound_exclusivity(object_editor_add, qtbot):
    """Тест взаємовиключності RF та Sound."""
    # Спочатку RF ввімкнено
    assert object_editor_add.ui.chkRFEnable.isChecked() is True
    
    # Вмикаємо Sound
    qtbot.mouseClick(object_editor_add.ui.chkSoundEnable, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)
    
    assert object_editor_add.ui.chkSoundEnable.isChecked() is True
    assert object_editor_add.ui.chkRFEnable.isChecked() is False
    assert object_editor_add.ui.lstRFFreqs.isEnabled() is False
    assert object_editor_add.ui.lstSoundFreqs.isEnabled() is True


def test_add_rf_range(object_editor_add, qtbot):
    """Тест додавання діапазону частот RF."""
    object_editor_add.ui.inpRFMin.setValue(2400.0)
    object_editor_add.ui.inpRFMax.setValue(2500.0)
    
    qtbot.mouseClick(object_editor_add.ui.btnAddRF, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)
    
    assert object_editor_add.ui.lstRFFreqs.count() == 1
    item = object_editor_add.ui.lstRFFreqs.item(0)
    assert "2400" in item.text() and "2500" in item.text()
    
    # Перевірка даних через роль
    data = item.data(Qt.ItemDataRole.UserRole)
    assert data == "2400000000-2500000000"


def test_save_new_object_success(object_editor_add, qtbot):
    """Тест успішного збереження нового об'єкта (тільки RF)."""
    object_editor_add.ui.inpName.clear()
    qtbot.keyClicks(object_editor_add.ui.inpName, "New Drone")
    object_editor_add.ui.comboClass.setCurrentIndex(0) # Drone
    
    # Додаємо частоту
    object_editor_add.ui.inpRFMin.setValue(433.0)
    object_editor_add.ui.inpRFMax.setValue(433.0)
    qtbot.mouseClick(object_editor_add.ui.btnAddRF, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)
    
    with qtbot.waitSignal(object_editor_add.finished, timeout=1000) as blocker:
        qtbot.mouseClick(object_editor_add.ui.btnSave, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)
    
    assert blocker.args == [QDialog.DialogCode.Accepted]
    obj = object_editor_add.get_new_object()
    assert obj.name == "New Drone"
    assert obj.class_id == 1
    assert "433000000-433000000" in obj.rf_params_hz


def test_save_validation_fail(object_editor_add, qtbot):
    """Тест провалу валідації (порожня назва)."""
    object_editor_add.ui.inpName.clear()
    with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_warn:
        qtbot.mouseClick(object_editor_add.ui.btnSave, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)
        assert mock_warn.called
    
    assert object_editor_add.result() == 0
