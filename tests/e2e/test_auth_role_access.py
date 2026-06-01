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
    """Перевірка обмеженого доступу до UI для ролі 'Оператор'.

    Сценарій тестує вхід під роллю Оператора та підтверджує, що критичні
    елементи керування (меню налаштувань, скидання помилкових тривог) приховані,
    оскільки оператор має доступ лише до моніторингу та базової навігації.

    Args:
        app_services: Фікстура з сервісами додатка.
        qtbot: Фікстура pytest-qt для взаємодії з UI.
        e2e_server: Фікстура запущеного тестового сервера.
    """
    settings = app_services["settings"]

    # Ініціалізація діалогу логіну з сервісами клавіатури для емуляції вводу
    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    # Очікуємо заповнення списку ролей (async-ініціалізація)
    qtbot.wait_until(lambda: login_dlg.ui.roleComboBox.count() > 0)
    # Індекс 0 відповідає ролі 'Operator' за замовчуванням
    login_dlg.ui.roleComboBox.setCurrentIndex(0)

    with qtbot.wait_signal(login_dlg.finished):
        qtbot.mouseClick(login_dlg.ui.loginButton, Qt.MouseButton.LeftButton)

    assert login_dlg.result() == QDialog.DialogCode.Accepted

    # Перевірка MainWindow UI після успішної авторизації
    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Оператор не повинен мати доступу до конфігурації системи та видалення подій
    assert main_win.ui.menuButton.isVisible() is False, (
        "Кнопка меню має бути прихована для Оператора для захисту конфігурації"
    )
    assert main_win.ui.falseAlarmButton.isVisible() is False, (
        "Кнопка скидання тривог має бути прихована для Оператора"
    )
    # Кнопка виходу має бути доступною для зміни користувача
    assert main_win.ui.backToLoginButton.isVisible() is True, (
        "Кнопка повернення до логіну має бути видимою для Оператора"
    )


def test_owner_login_full_ui(
    app_services: dict[str, Any], qtbot: Any, e2e_server: Any
) -> None:
    """Перевірка повного доступу до UI для ролі 'Власник'.

    Сценарій підтверджує, що після введення коректного пароля Власник
    отримує доступ до всіх функцій системи, включаючи налаштування
    та керування об'єктами.

    Args:
        app_services: Фікстура з сервісами додатка.
        qtbot: Фікстура pytest-qt для взаємодії з UI.
        e2e_server: Фікстура запущеного тестового сервера.
    """
    settings = app_services["settings"]
    from app.utils.password_utils import hash_password

    # Встановлюємо відомий хеш для перевірки авторизації
    settings.owner_password_hash = hash_password("admin")

    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    qtbot.wait_until(lambda: login_dlg.ui.roleComboBox.count() > 0)
    # Індекс 1 відповідає ролі 'Owner'
    login_dlg.ui.roleComboBox.setCurrentIndex(1)

    # Емуляція введення пароля користувачем
    qtbot.keyClicks(login_dlg.ui.passwordLineEdit, "admin")

    with qtbot.wait_signal(login_dlg.finished):
        qtbot.mouseClick(login_dlg.ui.loginButton, Qt.MouseButton.LeftButton)

    assert login_dlg.result() == QDialog.DialogCode.Accepted, (
        "Вхід Власника не вдався з коректним паролем"
    )

    main_win = MainWindow(settings, app_services["keyboard"], app_services["system"])
    qtbot.addWidget(main_win)
    main_win.show()

    # Власник має повні права на керування системою
    assert main_win.ui.menuButton.isVisible() is True, (
        "Кнопка меню має бути видимою для Власника"
    )
    assert main_win.ui.falseAlarmButton.isVisible() is True, (
        "Кнопка скидання тривог має бути видимою для Власника"
    )
    # У Власника кнопка Logout зазвичай прихована в головному UI (доступна через меню)
    assert main_win.ui.backToLoginButton.isVisible() is False, (
        "Кнопка швидкого логауту має бути прихована для Власника"
    )


def test_change_password_flow(app_services: dict[str, Any], qtbot: Any) -> None:
    """Перевірка сценарію зміни пароля власника.

    Тест перевіряє валідацію та збереження нового пароля в налаштуваннях
    після успішного підтвердження в діалоговому вікні.

    Args:
        app_services: Фікстура з сервісами додатка.
        qtbot: Фікстура pytest-qt для взаємодії з UI.
    """
    settings = app_services["settings"]
    settings.role = "owner"
    from app.utils.password_utils import hash_password

    # Підготовка початкового стану з відомим паролем
    settings.owner_password_hash = hash_password("old_pass")

    pwd_dlg = ChangePwdDialog(settings, app_services["keyboard"])
    qtbot.addWidget(pwd_dlg)
    pwd_dlg.show()

    # Введення та підтвердження нового пароля
    qtbot.keyClicks(pwd_dlg.ui.passwordLineEdit, "new_pass_123")
    qtbot.keyClicks(pwd_dlg.ui.confirmPasswordLineEdit, "new_pass_123")

    with qtbot.wait_signal(pwd_dlg.finished):
        qtbot.mouseClick(pwd_dlg.ui.saveButton, Qt.MouseButton.LeftButton)

    assert pwd_dlg.result() == QDialog.DialogCode.Accepted

    # Перевірка, що новий хеш відрізняється від старого та валідний для нового пароля
    from app.utils.password_utils import verify_password

    assert settings.owner_password_hash != hash_password("old_pass"), (
        "Хеш пароля не оновився"
    )
    assert verify_password("new_pass_123", settings.owner_password_hash) is True, (
        "Новий пароль не валідується"
    )


def test_logout_and_user_change_flow(
    app_services: dict[str, Any], qtbot: Any, e2e_server: Any
) -> None:
    """Перевірка циклу виходу (Logout) та скидання стану сесії.

    Тест гарантує, що при виході з системи:
    1. Скидається прапорець 'Запам'ятати мене'.
    2. Роль користувача повертається до значення за замовчуванням ('operator').
    3. Вікно логіну відображається з початковими налаштуваннями.

    Args:
        app_services: Фікстура з сервісами додатка.
        qtbot: Фікстура pytest-qt для взаємодії з UI.
        e2e_server: Фікстура запущеного тестового сервера.
    """
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

    # Перевірка очищення конфіденційних даних сесії
    assert settings.remember_me is False, (
        "Прапорець 'Remember me' має бути скинутий при виході"
    )
    assert settings.role == "operator", (
        "Роль має повернутися до 'operator' за замовчуванням"
    )

    # Перевірка стану діалогу логіну після логауту
    login_dlg = LoginDialog(settings, app_services["keyboard"])
    qtbot.addWidget(login_dlg)
    login_dlg.show()

    assert login_dlg.ui.roleComboBox.currentIndex() == 0, (
        "Діалог логіну має пропонувати роль Оператора за замовчуванням"
    )
