from PyQt6.QtWidgets import QDialog, QLineEdit
from PyQt6 import uic

from app.services.settings_service import SettingsService
from app.utils.password_utils import verify_password


class LoginDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        print("[LoginDialog] Ініціалізація діалогу входу...")

        self.settings_service = settings

        print("[LoginDialog] Завантаження UI...")
        uic.loadUi("app/ui/login_dialog.ui", self)

        role = self.settings_service.role
        print(f"[LoginDialog] Поточна роль із налаштувань: {role}")

        self.roleComboBox.currentIndexChanged.connect(self.toggle_password_field)
        self.roleComboBox.setCurrentIndex(0 if role == "operator" else 1)
        self.passwordLineEdit.textChanged.connect(self.change_password_status)

        self.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        self.loginButton.clicked.connect(self.handle_login)
        print("[LoginDialog] Сигнали підключено.")

    def toggle_password_field(self):
        """
        Показує або ховає контейнер з паролем
        залежно від обраної ролі.
        """
        current_role = self.roleComboBox.currentText()
        print(f"[toggle_password_field] Обрана роль: {current_role}")

        if current_role == "Власник":
            print("[toggle_password_field] Показуємо поле пароля")
            self.passwordContainer.setVisible(True)
        else:
            print("[toggle_password_field] Ховаємо поле пароля")
            self.passwordContainer.setVisible(False)

    def change_password_status(self):
        # Приховую Label зі статусом
        print(
            "[change_password_status] Зміна тексту в полі пароля — ховаємо мітку помилки."
        )
        self.passwordIncorrectLabel.setVisible(False)

    def hide_unhide_password(self):
        status = self.passwordHideBtn.property("status")
        print(f"[hide_unhide_password] Поточний статус: {status}")

        if status == "hidden":
            print("[hide_unhide_password] Відображаємо пароль.")
            self.passwordHideBtn.setProperty("status", "unhidden")
            self.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            print("[hide_unhide_password] Приховуємо пароль.")
            self.passwordHideBtn.setProperty("status", "hidden")
            self.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        self.passwordHideBtn.style().unpolish(self.passwordHideBtn)
        self.passwordHideBtn.style().polish(self.passwordHideBtn)
        self.passwordHideBtn.update()
        print("[hide_unhide_password] Оновлення стилю завершено.")

    def handle_login(self):
        role = self.roleComboBox.currentText()
        print(f"[handle_login] Користувач вибрав роль: {role}")

        if role == "Оператор":
            print("[handle_login] Вхід як оператор. Пропускаємо перевірку пароля.")
            self.settings_service.role = "operator"
            self.accept_window()
            return

        # 2. Логіка для Власника (потрібна перевірка пароля)
        if role == "Власник":
            print("[handle_login] Перевірка пароля для власника.")
            password = self.passwordLineEdit.text()
            real_password = self.settings_service.owner_password_hash

            is_password_correct = verify_password(password, real_password)
            print(f"[handle_login] Результат перевірки пароля: {is_password_correct}")

            if is_password_correct:
                remember = self.rememberCheckBox.isChecked()
                print(
                    f"[handle_login] Пароль правильний. Запам'ятати користувача: {remember}"
                )
                if remember:
                    self.settings_service.remember_me = remember

                self.settings_service.role = "owner"
                self.accept_window()
            else:
                print(
                    "[handle_login] Неправильний пароль. Показуємо повідомлення про помилку."
                )
                self.passwordIncorrectLabel.setVisible(True)

    def accept_window(self):
        print("[accept_window] Закриття діалогу з кодом Accepted.")
        self.finished.emit(QDialog.DialogCode.Accepted)
