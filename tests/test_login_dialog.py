"""
Тести для діалогу авторизації.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QDialog

from app.widgets.login_dialog import LoginDialog


@pytest.fixture
def mock_settings():
    """
    Фікстура для макета налаштувань.
    """
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
def mock_keyboard():
    """
    Фікстура для макета сервісу клавіатури.
    """
    mock = MagicMock()
    mock.current_layout = "EN"
    return mock


@pytest.fixture
def login_dialog(qtbot, mock_settings, mock_keyboard):
    """
    Фікстура для ініціалізації LoginDialog з моками.
    """
    # Мокаємо UsbAuthService, щоб він не запускав реальний потік моніторингу
    with patch("app.widgets.login_dialog.UsbAuthService"):
        dialog = LoginDialog(mock_settings, mock_keyboard)
        qtbot.addWidget(dialog)
        yield dialog
        from PyQt6.QtCore import QCoreApplication

        QCoreApplication.removeTranslator(dialog.translator)


def test_login_as_operator(login_dialog, mock_settings, qtbot) -> None:
    """
    Тест входу під роллю Оператора (без пароля).
    """
    # Обираємо роль оператора (індекс 0)
    login_dialog.ui.roleComboBox.setCurrentIndex(0)

    # Очікуємо сигнал finished
    with qtbot.waitSignal(login_dialog.finished, timeout=1000) as blocker:
        qtbot.mouseClick(
            login_dialog.ui.loginButton,
            pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
        )

    assert blocker.args == [QDialog.DialogCode.Accepted]
    assert mock_settings.role == "operator"


def test_login_as_owner_correct_password(login_dialog, mock_settings, qtbot) -> None:
    """
    Тест успішного входу під роллю Власника.
    """
    # Обираємо роль власника (індекс 1)
    login_dialog.ui.roleComboBox.setCurrentIndex(1)

    # Вводимо правильний пароль (мокаємо verify_password)
    with patch("app.widgets.login_dialog.verify_password", return_value=True):
        qtbot.keyClicks(login_dialog.ui.passwordLineEdit, "admin")

        # Очікуємо сигнал finished
        with qtbot.waitSignal(login_dialog.finished, timeout=1000) as blocker:
            qtbot.mouseClick(
                login_dialog.ui.loginButton,
                pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
            )

    assert blocker.args == [QDialog.DialogCode.Accepted]
    assert mock_settings.role == "owner"


def test_login_as_owner_incorrect_password(login_dialog, mock_settings, qtbot) -> None:
    """
    Тест невдалого входу з неправильним паролем.
    """
    login_dialog.ui.roleComboBox.setCurrentIndex(1)

    with patch("app.widgets.login_dialog.verify_password", return_value=False):
        qtbot.keyClicks(login_dialog.ui.passwordLineEdit, "wrong_password")
        qtbot.mouseClick(
            login_dialog.ui.loginButton,
            pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
        )

    # Перевіряємо, що з'явилося повідомлення про помилку
    assert not login_dialog.ui.passwordIncorrectLabel.isHidden()
    # Налаштування не повинні змінитись
    assert mock_settings.role != "owner"


def test_remember_me_functionality(login_dialog, mock_settings, qtbot) -> None:
    """
    Тест прапорця "Запам'ятати мене".
    """
    login_dialog.ui.roleComboBox.setCurrentIndex(1)
    login_dialog.ui.rememberCheckBox.setChecked(True)

    with patch("app.widgets.login_dialog.verify_password", return_value=True):
        qtbot.keyClicks(login_dialog.ui.passwordLineEdit, "admin")

        with qtbot.waitSignal(login_dialog.finished, timeout=1000):
            qtbot.mouseClick(
                login_dialog.ui.loginButton,
                pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
            )

    assert mock_settings.remember_me is True


def test_toggle_password_visibility(login_dialog, qtbot) -> None:
    """
    Тест перемикання видимості пароля.
    """
    from PyQt6.QtWidgets import QLineEdit

    # Спочатку пароль прихований
    assert login_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Password

    # Натискаємо кнопку ока
    qtbot.mouseClick(
        login_dialog.ui.passwordHideBtn,
        pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
    )
    assert login_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Normal

    # Натискаємо ще раз
    qtbot.mouseClick(
        login_dialog.ui.passwordHideBtn,
        pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
    )
    assert login_dialog.ui.passwordLineEdit.echoMode() == QLineEdit.EchoMode.Password
