"""
Тести для діалогу зміни пароля.
"""

from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QDialog, QLineEdit

from app.widgets.change_pwd_dialog import ChangePwdDialog


@pytest.fixture
def mock_settings():
    """Фікстура для макета налаштувань."""
    settings = MagicMock()
    settings.lang_code = "uk"
    settings.owner_password_hash = ""
    return settings


@pytest.fixture
def mock_keyboard():
    """Фікстура для макета сервісу клавіатури."""
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def change_pwd_dialog(qtbot, mock_settings, mock_keyboard):
    """Фікстура для ініціалізації ChangePwdDialog з моками."""
    dialog = ChangePwdDialog(mock_settings, mock_keyboard)
    qtbot.addWidget(dialog)
    yield dialog
    # Очищуємо транслятори
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.removeTranslator(dialog.translator)


def test_ui_initialization(change_pwd_dialog):
    """Тест ініціалізації інтерфейсу."""
    assert change_pwd_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Password
    assert change_pwd_dialog.ui.confirmPasswordLineEdit.echoMode() == QLineEdit.EchoMode.Password
    assert change_pwd_dialog.ui.errorWidget_1.isHidden()
    assert change_pwd_dialog.ui.errorWidget_2.isHidden()


def test_password_mismatch(change_pwd_dialog, qtbot):
    """Тест помилки при незбігу паролів."""
    change_pwd_dialog.ui.passwordLineEdit.clear()
    change_pwd_dialog.ui.confirmPasswordLineEdit.clear()

    qtbot.keyClicks(change_pwd_dialog.ui.passwordLineEdit, "StrongPass123")
    qtbot.keyClicks(change_pwd_dialog.ui.confirmPasswordLineEdit, "DifferentPass123")

    qtbot.mouseClick(change_pwd_dialog.ui.saveButton, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)

    # Використовуємо isHidden() замість isVisible(), бо діалог може бути не показаний реально
    assert not change_pwd_dialog.ui.errorWidget_2.isHidden()


def test_password_validation_fail(change_pwd_dialog, qtbot):
    """Тест провалу валідації (дуже короткий пароль)."""
    change_pwd_dialog.ui.passwordLineEdit.clear()
    change_pwd_dialog.ui.confirmPasswordLineEdit.clear()

    # Пароль занадто короткий (менше 4 символів)
    qtbot.keyClicks(change_pwd_dialog.ui.passwordLineEdit, "123")
    qtbot.keyClicks(change_pwd_dialog.ui.confirmPasswordLineEdit, "123")

    qtbot.mouseClick(change_pwd_dialog.ui.saveButton, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)

    assert not change_pwd_dialog.ui.errorWidget_1.isHidden()


def test_successful_password_change(change_pwd_dialog, mock_settings, qtbot):
    """Тест успішної зміни пароля."""
    change_pwd_dialog.ui.passwordLineEdit.clear()
    change_pwd_dialog.ui.confirmPasswordLineEdit.clear()

    password = "ValidPassword123!"
    qtbot.keyClicks(change_pwd_dialog.ui.passwordLineEdit, password)
    qtbot.keyClicks(change_pwd_dialog.ui.confirmPasswordLineEdit, password)

    with qtbot.waitSignal(change_pwd_dialog.finished, timeout=1000) as blocker:
        qtbot.mouseClick(change_pwd_dialog.ui.saveButton, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)

    assert blocker.args == [QDialog.DialogCode.Accepted]
    assert mock_settings.owner_password_hash.startswith("$2b$")


def test_toggle_visibility(change_pwd_dialog, qtbot):
    """Тест перемикання видимості паролів."""
    # Перше поле
    assert change_pwd_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Password
    qtbot.mouseClick(change_pwd_dialog.ui.passwordHideBtn, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)
    assert change_pwd_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Normal

    # Друге поле
    assert change_pwd_dialog.ui.confirmPasswordLineEdit.echoMode() == QLineEdit.EchoMode.Password
    qtbot.mouseClick(change_pwd_dialog.ui.confirmPasswordHideBtn, pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton)
    assert change_pwd_dialog.ui.confirmPasswordLineEdit.echoMode() == QLineEdit.EchoMode.Normal
