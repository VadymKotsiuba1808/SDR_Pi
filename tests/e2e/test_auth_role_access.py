"""
E2E тести для перевірки авторизації та розмежування прав доступу (RBAC).
"""

from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from app.widgets.change_pwd_dialog import ChangePwdDialog
from app.widgets.login_dialog import LoginDialog
from app.widgets.main_window import MainWindow


def test_operator_login_restricted_ui(app_services, qtbot, e2e_server):
    """
    Сценарій 1: Вхід під роллю 'Оператор' (обмежений UI).
    """
    settings = app_services["settings"]

    # 1. Login as Operator
    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    # Вибираємо роль Operator (index 0)
    qtbot.wait_until(lambda: login_dlg.ui.roleComboBox.count() > 0)
    login_dlg.ui.roleComboBox.setCurrentIndex(0)

    with qtbot.wait_signal(login_dlg.finished):
        qtbot.mouseClick(login_dlg.ui.loginButton, Qt.MouseButton.LeftButton)

    assert login_dlg.result() == QDialog.DialogCode.Accepted

    # 2. Check MainWindow UI
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Для Оператора:
    # menuButton має бути приховано
    # falseAlarmButton має бути приховано
    # backToLoginButton має бути видимим
    assert main_win.ui.menuButton.isVisible() is False, (
        "Menu button should be hidden for Operator"
    )
    assert main_win.ui.falseAlarmButton.isVisible() is False, (
        "False alarm button should be hidden for Operator"
    )
    assert main_win.ui.backToLoginButton.isVisible() is True, (
        "Logout button should be visible for Operator"
    )


def test_owner_login_full_ui(app_services, qtbot, e2e_server):
    """
    Сценарій 2: Вхід під роллю 'Власник' (повний доступ).
    """
    settings = app_services["settings"]
    # Встановлюємо тестовий пароль 'admin'
    from app.utils.password_utils import hash_password

    settings.owner_password_hash = hash_password("admin")

    # 1. Login as Owner
    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    # Вибираємо роль Owner (index 1)
    qtbot.wait_until(lambda: login_dlg.ui.roleComboBox.count() > 0)
    login_dlg.ui.roleComboBox.setCurrentIndex(1)

    # Вводимо пароль
    qtbot.keyClicks(login_dlg.ui.passwordLineEdit, "admin")

    with qtbot.wait_signal(login_dlg.finished):
        qtbot.mouseClick(login_dlg.ui.loginButton, Qt.MouseButton.LeftButton)

    assert login_dlg.result() == QDialog.DialogCode.Accepted, "Owner login failed"

    # 2. Check MainWindow UI
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Для Власника:
    # menuButton має бути видимим
    # falseAlarmButton має бути видимим (але може бути disabled поки немає цілі)
    assert main_win.ui.menuButton.isVisible() is True, (
        "Menu button should be visible for Owner"
    )
    assert main_win.ui.falseAlarmButton.isVisible() is True, (
        "False alarm button should be visible for Owner"
    )
    assert main_win.ui.backToLoginButton.isVisible() is False, (
        "Logout button should be hidden for Owner"
    )


def test_change_password_flow(app_services, qtbot):
    """
    Сценарій 3: Зміна пароля власника.
    """
    settings = app_services["settings"]
    settings.role = "owner"
    from app.utils.password_utils import hash_password

    settings.owner_password_hash = hash_password("old_pass")

    # Створюємо діалог зміни пароля
    pwd_dlg = ChangePwdDialog(settings, app_services["keyboard"])
    qtbot.addWidget(pwd_dlg)
    pwd_dlg.show()

    # 1. Вводимо новий пароль
    qtbot.keyClicks(pwd_dlg.ui.passwordLineEdit, "new_pass_123")
    qtbot.keyClicks(pwd_dlg.ui.confirmPasswordLineEdit, "new_pass_123")

    # 2. Натискаємо зберегти
    with qtbot.wait_signal(pwd_dlg.finished):
        qtbot.mouseClick(pwd_dlg.ui.saveButton, Qt.MouseButton.LeftButton)

    assert pwd_dlg.result() == QDialog.DialogCode.Accepted

    # 3. Перевіряємо, що хеш змінився та валідний для нового пароля
    from app.utils.password_utils import verify_password

    assert settings.owner_password_hash != hash_password("old_pass")
    assert verify_password("new_pass_123", settings.owner_password_hash) is True


def test_logout_and_user_change_flow(app_services, qtbot, e2e_server):
    """
    Сценарій 18: Повний цикл виходу (Logout) та зміна користувача.
    """
    settings = app_services["settings"]
    settings.role = "owner"
    settings.remember_me = True

    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # 1. Натискаємо вихід (у Власника це зазвичай через меню або спеціальну кнопку,
    # якщо її немає прямо в UI, ми викликаємо метод restart_app)
    # Оскільки ми мокаємо перезапуск, ми просто перевіряємо логіку скидання.
    with patch("PyQt6.QtWidgets.QApplication.quit"):  # Запобігаємо реальному закриттю
        main_win.restart_app()

    # 2. Перевіряємо скидання налаштувань
    assert settings.remember_me is False, "Remember me should be cleared on logout"
    assert settings.role == "operator", "Role should revert to default operator"

    # 3. Емулюємо повернення до вікна логіну
    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    assert login_dlg.ui.roleComboBox.currentIndex() == 0, (
        "Should default back to Operator"
    )
