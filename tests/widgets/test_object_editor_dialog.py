"""Модуль для тестування діалогу редагування об'єктів виявлення."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QDialog

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.widgets.object_editor_dialog import ObjectEditorDialog


@pytest.fixture
def mock_settings() -> MagicMock:
    """Створює макет налаштувань програми."""
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def mock_keyboard() -> MagicMock:
    """Створює макет сервісу віртуальної клавіатури."""
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def known_classes() -> list[ObjectClass]:
    """Надає список попередньо визначених класів об'єктів."""
    return [
        ObjectClass(id=1, name="Drone"),
        ObjectClass(id=2, name="Bird"),
    ]


@pytest.fixture
def object_editor_add(
    qtbot,
    mock_settings: MagicMock,
    mock_keyboard: MagicMock,
    known_classes: list[ObjectClass],
) -> Generator[ObjectEditorDialog, None, None]:
    """Створює діалог у режимі додавання."""
    dialog = ObjectEditorDialog(mock_settings, mock_keyboard, known_classes)
    qtbot.addWidget(dialog)
    yield dialog

    if hasattr(dialog, "translator"):
        QCoreApplication.removeTranslator(dialog.translator)


@pytest.fixture
def object_editor_edit(
    qtbot,
    mock_settings: MagicMock,
    mock_keyboard: MagicMock,
    known_classes: list[ObjectClass],
) -> Generator[ObjectEditorDialog, None, None]:
    """Створює діалог у режимі редагування."""
    obj = DetectionObject(
        id=10,
        name="Existing Object",
        class_id=1,
        object_class="Drone",
        is_dangerous=True,
        rf_params_hz=["2400000000-2483500000"],
        sound_params_hz=[],
    )
    dialog = ObjectEditorDialog(
        mock_settings, mock_keyboard, known_classes, object_data=obj
    )
    qtbot.addWidget(dialog)
    yield dialog

    if hasattr(dialog, "translator"):
        QCoreApplication.removeTranslator(dialog.translator)


def test_add_mode_initial_state(object_editor_add: ObjectEditorDialog) -> None:
    """Перевіряє стан віджетів у режимі додавання."""
    assert object_editor_add.ui.inpName.text() == ""
    assert object_editor_add.ui.comboClass.count() == 2
    assert object_editor_add.ui.chkRFEnable.isChecked() is True
    assert object_editor_add.ui.chkSoundEnable.isChecked() is False


def test_edit_mode_loading(object_editor_edit: ObjectEditorDialog) -> None:
    """Перевіряє завантаження даних існуючого об'єкта."""
    assert object_editor_edit.ui.inpName.text() == "Existing Object"
    assert object_editor_edit.ui.comboClass.currentText() == "Drone"
    assert object_editor_edit.ui.chkDangerous.isChecked() is True
    assert object_editor_edit.ui.lstRFFreqs.count() == 1


def test_toggle_rf_sound_exclusivity(
    object_editor_add: ObjectEditorDialog, qtbot
) -> None:
    """Перевіряє взаємовиключність RF та звуку."""
    assert object_editor_add.ui.chkRFEnable.isChecked() is True

    qtbot.mouseClick(
        object_editor_add.ui.chkSoundEnable,
        Qt.MouseButton.LeftButton,
    )

    assert object_editor_add.ui.chkSoundEnable.isChecked() is True
    assert object_editor_add.ui.chkRFEnable.isChecked() is False
    assert object_editor_add.ui.lstRFFreqs.isEnabled() is False
    assert object_editor_add.ui.lstSoundFreqs.isEnabled() is True


def test_add_rf_range(object_editor_add: ObjectEditorDialog, qtbot) -> None:
    """Перевіряє додавання діапазону частот RF."""
    object_editor_add.ui.inpRFMin.setValue(2400.0)
    object_editor_add.ui.inpRFMax.setValue(2500.0)

    qtbot.mouseClick(
        object_editor_add.ui.btnAddRF,
        Qt.MouseButton.LeftButton,
    )

    assert object_editor_add.ui.lstRFFreqs.count() == 1
    item = object_editor_add.ui.lstRFFreqs.item(0)
    assert item is not None, "RF frequency list should have an item"
    assert "2400" in item.text() and "2500" in item.text()

    data = item.data(Qt.ItemDataRole.UserRole)
    assert data == "2400000000-2500000000"


def test_save_new_object_success(object_editor_add: ObjectEditorDialog, qtbot) -> None:
    """Перевіряє успішне збереження об'єкта."""
    object_editor_add.ui.inpName.clear()
    qtbot.keyClicks(object_editor_add.ui.inpName, "New Drone")
    object_editor_add.ui.comboClass.setCurrentIndex(0)

    object_editor_add.ui.inpRFMin.setValue(433.0)
    object_editor_add.ui.inpRFMax.setValue(433.0)
    qtbot.mouseClick(
        object_editor_add.ui.btnAddRF,
        Qt.MouseButton.LeftButton,
    )

    with qtbot.waitSignal(object_editor_add.finished, timeout=1000) as blocker:
        qtbot.mouseClick(
            object_editor_add.ui.btnSave,
            Qt.MouseButton.LeftButton,
        )

    assert blocker.args == [QDialog.DialogCode.Accepted]
    obj = object_editor_add.get_new_object()
    assert obj is not None, "Створений об'єкт не повинен бути None"
    assert obj.name == "New Drone"
    assert obj.class_id == 1
    assert "433000000-433000000" in obj.rf_params_hz


def test_save_validation_fail(object_editor_add: ObjectEditorDialog, qtbot) -> None:
    """Перевіряє валідацію збереження при порожньому імені."""
    object_editor_add.ui.inpName.clear()
    with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_warn:
        qtbot.mouseClick(
            object_editor_add.ui.btnSave,
            Qt.MouseButton.LeftButton,
        )
        assert mock_warn.called

    assert object_editor_add.result() == 0
