"""
Діалог авторизації.
Логіка вікна входу: обробка вводу пароля та перехід до головного вікна.
"""

from typing import Optional, cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, QTranslator
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QDialog, QLineEdit, QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.protocols import LoginDialogSettings
from app.services.keyboard_service import KeyboardService
from app.services.usb_auth_service import UsbAuthService
from app.ui.ui_login_dialog import Ui_LoginDialog
from app.utils.password_utils import verify_password
from app.utils.ui_utils import update_element_styles
from app.widgets.autosize_window import make_window_stretched
from app.widgets.change_pwd_dialog import ChangePwdDialog
from app.widgets.keyboard_widget import KeyboardWidget


class LoginDialog(QDialog):
    def __init__(
        self,
        settings: LoginDialogSettings,
        keyboard: KeyboardService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        print("[LoginDialog] Initializing login dialog...")

        self.settings_service = settings
        self.keyboard_service = keyboard

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()

        self.toggle_password_field()
        self._load_language()
        print("[LoginDialog] Initialization complete.")

    def changeEvent(self, a0: QEvent | None) -> None:
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                print("[LoginDialog] Language change detected, updating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_LoginDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/login_dialog.ui", self)
            self.ui = cast(Ui_LoginDialog, self)

    def _setup_state_variables(self) -> None:
        self.translator = QTranslator()
        self.keyboard_widget = KeyboardWidget(
            self.settings_service, self.keyboard_service, parent=self
        )

        self.auth_service = UsbAuthService()
        self.auth_service.auth_success_signal.connect(self.on_usb_reset_request)
        self.auth_service.start_monitoring()

    def _adjust_fields(self) -> None:
        role = self.settings_service.role

        self.ui.roleComboBox.setCurrentIndex(0 if role == "operator" else 1)
        self.ui.keyboardLayout.addWidget(self.keyboard_widget)

    def _connect_handlers(self) -> None:
        self.ui.roleComboBox.currentIndexChanged.connect(self.toggle_password_field)
        self.ui.passwordLineEdit.textChanged.connect(self.change_password_status)
        self.ui.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        self.ui.loginButton.clicked.connect(self.handle_login)

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code

        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"[LoginDialog] Error: Failed to load translation file: {path}")

    def on_usb_reset_request(self) -> None:

        print("[LoginDialog] USB Key detected. Opening password change dialog.")
        self.change_pwd_dialog = ChangePwdDialog(
            self.settings_service, self.keyboard_service
        )
        make_window_stretched(self.change_pwd_dialog)
        self.change_pwd_dialog.showFullScreen()

    def toggle_password_field(self) -> None:
        current_index = self.ui.roleComboBox.currentIndex()

        if current_index == 1:
            self.ui.passwordContainer.setVisible(True)
        else:
            self.ui.passwordContainer.setVisible(False)

    def change_password_status(self) -> None:
        self.ui.passwordIncorrectLabel.setVisible(False)

    def hide_unhide_password(self) -> None:
        status = self.ui.passwordHideBtn.property("status")

        if status == "hidden":
            self.ui.passwordHideBtn.setProperty("status", "unhidden")
            self.ui.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.ui.passwordHideBtn.setProperty("status", "hidden")
            self.ui.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        update_element_styles(self.ui.passwordHideBtn)

    def handle_login(self) -> None:
        index = self.ui.roleComboBox.currentIndex()

        if index == 0:
            print("[LoginDialog] Logging in as Operator (no password required).")
            self.settings_service.role = "operator"
            self.accept_window()
            return

        if index == 1:
            password = self.ui.passwordLineEdit.text()
            real_password_hash = self.settings_service.owner_password_hash

            if verify_password(password, real_password_hash):
                remember = self.ui.rememberCheckBox.isChecked()
                print(f"[LoginDialog] Login successful. Remember me: {remember}")

                if remember:
                    self.settings_service.remember_me = remember

                self.settings_service.role = "owner"
                self.accept_window()
            else:
                print("[LoginDialog] Login failed: Incorrect password.")
                self.ui.passwordIncorrectLabel.setVisible(True)

    def accept_window(self) -> None:
        self.finished.emit(QDialog.DialogCode.Accepted)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        event = a0

        if hasattr(self, "auth_service"):
            self.auth_service.stop_monitoring()

        self.done(QDialog.DialogCode.Rejected)
        if event:
            event.accept()
