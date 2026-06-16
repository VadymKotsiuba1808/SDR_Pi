"""Модуль e2e тестів для перевірки авторизації та розмежування прав доступу (RBAC).

Цей модуль містить сценарії тестування входу в систему під різними ролями (Оператор, Власник),
перевірки відповідності графічного інтерфейсу (UI) правам доступу, а також
процедур зміни пароля та виходу з системи.
"""

from typing import Any
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from app.widgets.change_pwd_dialog import ChangePwdDialog
from app.widgets.login_dialog import LoginDialog
from app.widgets.main_window import MainWindow


def test_operator_login_restricted_ui(
    app_services: dict[str, Any], qtbot: Any, e2e_server: Any
) -> None:
    """Перевірка обмеженого доступу до UI для ролі 'Оператор'."""
    settings = app_services["settings"]

    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    # Очікуємо заповнення списку ролей (async-ініціалізація з БД)
    qtbot.wait_until(lambda: login_dlg.ui.roleComboBox.count() > 0)

    login_dlg.ui.roleComboBox.setCurrentIndex(0)

    with qtbot.wait_signal(login_dlg.finished):
        qtbot.mouseClick(login_dlg.ui.loginButton, Qt.MouseButton.LeftButton)

    assert login_dlg.result() == QDialog.DialogCode.Accepted

    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Оператор не повинен мати доступу до конфігурації системи та видалення подій
    assert main_win.ui.menuButton.isVisible() is False, (
        "Menu button should be hidden for Operator to protect configuration"
    )
    assert main_win.ui.falseAlarmButton.isVisible() is False, (
        "False alarm button should be hidden for Operator"
    )
    assert main_win.ui.backToLoginButton.isVisible() is True, (
        "Back to login button should be visible for Operator"
    )


def test_owner_login_full_ui(
    app_services: dict[str, Any], qtbot: Any, e2e_server: Any
) -> None:
    """Перевірка повного доступу до UI для ролі 'Власник'."""
    settings = app_services["settings"]
    from app.utils.password_utils import hash_password

    settings.owner_password_hash = hash_password("admin")

    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    qtbot.wait_until(lambda: login_dlg.ui.roleComboBox.count() > 0)
    login_dlg.ui.roleComboBox.setCurrentIndex(1)

    qtbot.keyClicks(login_dlg.ui.passwordLineEdit, "admin")

    with qtbot.wait_signal(login_dlg.finished):
        qtbot.mouseClick(login_dlg.ui.loginButton, Qt.MouseButton.LeftButton)

    assert login_dlg.result() == QDialog.DialogCode.Accepted, (
        "Owner login failed with correct password"
    )

    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Власник має повні права на керування системою
    assert main_win.ui.menuButton.isVisible() is True, (
        "Menu button should be visible for Owner"
    )
    assert main_win.ui.falseAlarmButton.isVisible() is True, (
        "False alarm button should be visible for Owner"
    )
    assert main_win.ui.backToLoginButton.isVisible() is False, (
        "Quick logout button should be hidden for Owner"
    )


def test_change_password_flow(app_services: dict[str, Any], qtbot: Any) -> None:
    """Перевірка сценарію зміни пароля власника."""
    settings = app_services["settings"]
    settings.role = "owner"
    from app.utils.password_utils import hash_password

    settings.owner_password_hash = hash_password("old_pass")

    pwd_dlg = ChangePwdDialog(settings, app_services["keyboard"])
    qtbot.addWidget(pwd_dlg)
    pwd_dlg.show()

    qtbot.keyClicks(pwd_dlg.ui.passwordLineEdit, "new_pass_123")
    qtbot.keyClicks(pwd_dlg.ui.confirmPasswordLineEdit, "new_pass_123")

    with qtbot.wait_signal(pwd_dlg.finished):
        qtbot.mouseClick(pwd_dlg.ui.saveButton, Qt.MouseButton.LeftButton)

    assert pwd_dlg.result() == QDialog.DialogCode.Accepted

    from app.utils.password_utils import verify_password

    assert settings.owner_password_hash != hash_password("old_pass"), (
        "Password hash did not update"
    )
    assert verify_password("new_pass_123", settings.owner_password_hash) is True, (
        "New password does not validate"
    )


def test_logout_and_user_change_flow(
    app_services: dict[str, Any], qtbot: Any, e2e_server: Any
) -> None:
    """Перевірка циклу виходу (Logout) та скидання стану сесії."""
    settings = app_services["settings"]
    settings.role = "owner"
    settings.remember_me = True

    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Емуляція виходу через метод restart_app. Патчимо QApplication.quit,
    # щоб уникнути завершення тестового процесу.
    with patch("PyQt6.QtWidgets.QApplication.quit"):
        main_win.restart_app()

    assert settings.remember_me is False, "'Remember me' flag should be reset on logout"
    assert settings.role == "operator", "Role should revert to 'operator' by default"

    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    assert login_dlg.ui.roleComboBox.currentIndex() == 0, (
        "Login dialog should offer Operator role by default"
    )
