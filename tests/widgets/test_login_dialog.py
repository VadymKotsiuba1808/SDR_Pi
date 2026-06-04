"""Тести для віджета діалогу авторизації LoginDialog."""

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QDialog

from app.widgets.login_dialog import LoginDialog


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.role = "operator"
    # Хеш для пароля "admin" (bcrypt)
    settings.owner_password_hash = (
        "$2b$12$8K6Bf.nF0vV6.zX6.zX6.u5l.u5l.u5l.u5l.u5l.u5l.u5l.u5l"
    )
    settings.remember_me = False
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def mock_keyboard() -> MagicMock:
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def login_dialog(
    qtbot, mock_settings: MagicMock, mock_keyboard: MagicMock
) -> Generator[LoginDialog, None, None]:
    with patch("app.widgets.login_dialog.UsbAuthService"):
        dialog = LoginDialog(mock_settings, mock_keyboard)
        qtbot.addWidget(dialog)
        yield dialog
        from PyQt6.QtCore import QCoreApplication

        QCoreApplication.removeTranslator(dialog.translator)


def test_login_as_operator(
    login_dialog: LoginDialog, mock_settings: MagicMock, qtbot
) -> None:
    """Перевіряє вхід до системи з роллю 'Оператор'."""
    login_dialog.ui.roleComboBox.setCurrentIndex(0)

    with qtbot.waitSignal(login_dialog.finished, timeout=1000) as blocker:
        qtbot.mouseClick(
            login_dialog.ui.loginButton,
            pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
        )

    assert blocker.args == [QDialog.DialogCode.Accepted], (
        "Dialog should return Accepted"
    )
    assert mock_settings.role == "operator", "Role should be set to operator"


def test_login_as_owner_correct_password(
    login_dialog: LoginDialog, mock_settings: MagicMock, qtbot
) -> None:
    """Перевіряє успішний вхід до системи з роллю 'Власник' та вірним паролем."""
    login_dialog.ui.roleComboBox.setCurrentIndex(1)

    with patch("app.widgets.login_dialog.verify_password", return_value=True):
        qtbot.keyClicks(login_dialog.ui.passwordLineEdit, "admin")

        with qtbot.waitSignal(login_dialog.finished, timeout=1000) as blocker:
            qtbot.mouseClick(
                login_dialog.ui.loginButton,
                pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
            )

    assert blocker.args == [QDialog.DialogCode.Accepted], (
        "Dialog should return Accepted"
    )
    assert mock_settings.role == "owner", "Role should be changed to owner"


def test_login_as_owner_incorrect_password(
    login_dialog: LoginDialog, mock_settings: MagicMock, qtbot
) -> None:
    """Перевіряє поведінку системи при спробі входу з невірним паролем власника."""
    login_dialog.ui.roleComboBox.setCurrentIndex(1)

    with patch("app.widgets.login_dialog.verify_password", return_value=False):
        qtbot.keyClicks(login_dialog.ui.passwordLineEdit, "wrong_password")
        qtbot.mouseClick(
            login_dialog.ui.loginButton,
            pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
        )

    assert not login_dialog.ui.passwordIncorrectLabel.isHidden(), (
        "Error message should be displayed"
    )
    assert mock_settings.role != "owner", "Role should not be changed to owner"


def test_remember_me_functionality(
    login_dialog: LoginDialog, mock_settings: MagicMock, qtbot
) -> None:
    """Перевіряє збереження опції 'Запам'ятати мене'."""
    login_dialog.ui.roleComboBox.setCurrentIndex(1)
    login_dialog.ui.rememberCheckBox.setChecked(True)

    with patch("app.widgets.login_dialog.verify_password", return_value=True):
        qtbot.keyClicks(login_dialog.ui.passwordLineEdit, "admin")

        with qtbot.waitSignal(login_dialog.finished, timeout=1000):
            qtbot.mouseClick(
                login_dialog.ui.loginButton,
                pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
            )

    assert mock_settings.remember_me is True, (
        "remember_me parameter should be set to True"
    )


def test_toggle_password_visibility(login_dialog: LoginDialog, qtbot) -> None:
    """Перевіряє функціональність перемикання видимості пароля."""
    from PyQt6.QtWidgets import QLineEdit

    assert login_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Password

    qtbot.mouseClick(
        login_dialog.ui.passwordHideBtn,
        pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
    )
    assert login_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Normal

    qtbot.mouseClick(
        login_dialog.ui.passwordHideBtn,
        pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
    )
    assert login_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Password
