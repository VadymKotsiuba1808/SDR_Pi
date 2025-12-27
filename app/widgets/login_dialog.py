"""
Діалог авторизації.
Логіка вікна входу: обробка вводу пароля та перехід до головного вікна.
"""

from PyQt6.QtWidgets import QDialog, QLineEdit
from PyQt6.QtCore import QCoreApplication, QTranslator, QEvent

from PyQt6 import uic

from app.ui.ui_login_dialog import Ui_LoginDialog

from app.protocols import LoginDialogSettings
from app.utils.password_utils import verify_password
from app.utils.ui_utils import update_element_styles
from app.widgets.keyboard_widget import KeyboardWidget
from app.widgets.change_pwd_dialog import ChangePwdDialog
from app.widgets.autosize_window import make_window_stretched
from app.services.keyboard_service import KeyboardService
from app.services.usb_auth_service import UsbAuthService


class LoginDialog(QDialog):
    def __init__(
        self, settings: LoginDialogSettings, keyboard: KeyboardService, parent=None
    ):
        super().__init__(parent)
        print("[LoginDialog] Ініціалізація діалогу входу...")

        self.settings_service = settings
        self.keyboard_service = keyboard

        print("[LoginDialog] Завантаження UI...")
        self._load_ui()

        self._setup_state_variables()

        self._adjust_fields()

        self._connect_handlers()
        print("[LoginDialog] Сигнали підключено.")

        self.toggle_password_field()
        self._load_language()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("Зміна мови, оновлюю UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_LoginDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/login_dialog.ui", self)
            self.ui = self

    def _setup_state_variables(self):
        self.translator = QTranslator()
        self.keyboard_widget = KeyboardWidget(
            self.settings_service, self.keyboard_service, parent=self
        )

        self.auth_service = UsbAuthService()
        self.auth_service.auth_success_signal.connect(self.on_usb_reset_request)
        self.auth_service.start_monitoring()

    def _adjust_fields(self):
        role = self.settings_service.role
        self.ui.roleComboBox.setCurrentIndex(0 if role == "operator" else 1)
        self.ui.keyboardLayout.addWidget(self.keyboard_widget)

    def _connect_handlers(self):
        self.ui.roleComboBox.currentIndexChanged.connect(self.toggle_password_field)

        self.ui.passwordLineEdit.textChanged.connect(self.change_password_status)

        self.ui.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        self.ui.loginButton.clicked.connect(self.handle_login)

    def _load_language(self):
        lang_code = self.settings_service.lang_code

        if lang_code == None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    def on_usb_reset_request(self):
        self.change_pwd_dialog = ChangePwdDialog(
            self.settings_service, self.keyboard_service
        )
        make_window_stretched(self.change_pwd_dialog)
        self.change_pwd_dialog.showFullScreen()

    def toggle_password_field(self):
        """
        Показує або ховає контейнер з паролем
        залежно від обраної ролі.
        """
        current_index = self.ui.roleComboBox.currentIndex()

        if current_index == 1:
            print("[toggle_password_field] Показуємо поле пароля")
            self.ui.passwordContainer.setVisible(True)
        else:
            print("[toggle_password_field] Ховаємо поле пароля")
            self.ui.passwordContainer.setVisible(False)

    def change_password_status(self):
        print(
            "[change_password_status] Зміна тексту в полі пароля — ховаємо мітку помилки."
        )
        self.ui.passwordIncorrectLabel.setVisible(False)

    def hide_unhide_password(self):
        status = self.ui.passwordHideBtn.property("status")
        print(f"[hide_unhide_password] Поточний статус: {status}")

        if status == "hidden":
            print("[hide_unhide_password] Відображаємо пароль.")
            self.ui.passwordHideBtn.setProperty("status", "unhidden")
            self.ui.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            print("[hide_unhide_password] Приховуємо пароль.")
            self.ui.passwordHideBtn.setProperty("status", "hidden")
            self.ui.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        update_element_styles(self.ui.passwordHideBtn)
        print("[hide_unhide_password] Оновлення стилю завершено.")

    def handle_login(self):
        index = self.ui.roleComboBox.currentIndex()

        if index == 0:
            print("[handle_login] Вхід як оператор. Пропускаємо перевірку пароля.")
            self.settings_service.role = "operator"
            self.accept_window()
            return

        if index == 1:
            print("[handle_login] Перевірка пароля для власника.")
            password = self.ui.passwordLineEdit.text()
            real_password = self.settings_service.owner_password_hash

            is_password_correct = verify_password(password, real_password)
            print(f"[handle_login] Результат перевірки пароля: {is_password_correct}")

            if is_password_correct:
                remember = self.ui.rememberCheckBox.isChecked()
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
                self.ui.passwordIncorrectLabel.setVisible(True)

    def accept_window(self):
        print("[accept_window] Закриття діалогу з кодом Accepted.")
        self.finished.emit(QDialog.DialogCode.Accepted)

    def closeEvent(self, event):
        if self.auth_service:
            self.auth_service.stop_monitoring()
        event.accept()
