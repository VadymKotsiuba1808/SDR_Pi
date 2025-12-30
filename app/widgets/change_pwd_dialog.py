from typing import Optional

from PyQt6.QtWidgets import QDialog, QLineEdit, QWidget, QPushButton
from PyQt6.QtCore import QCoreApplication, QEvent, QTranslator, Qt
from PyQt6 import uic

from app.protocols import ChangePwdDialogSettings
from app.ui.ui_change_pwd_dialog import Ui_ChangePwdDialog
from app.widgets.keyboard_widget import KeyboardWidget
from app.services.keyboard_service import KeyboardService
from app.validators.password_validator import PasswordValidator
from app.utils.password_utils import hash_password
from app.utils.ui_utils import update_element_styles


class ChangePwdDialog(QDialog):
    """
    Діалог зміни пароля.
    Реалізує логіку інтерфейсу для оновлення облікових даних: валідація нового та збереження змін.
    """

    def __init__(
        self,
        settings: ChangePwdDialogSettings,
        keyboard: KeyboardService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.settings_service = settings
        self.keyboard_service = keyboard
        self.translator = QTranslator()

        self._load_ui()
        print("[ChangePwdDialog] Interface loaded.")

        self._adjust_fields()
        self._connect_handlers()
        self._load_language()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("[ChangePwdDialog] Language change detected, updating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_ChangePwdDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/change_pwd_dialog.ui", self)
            self.ui = self

    def _adjust_fields(self) -> None:
        self.keyboard_widget = KeyboardWidget(
            self.settings_service, self.keyboard_service, parent=self
        )
        self.ui.keyboardLayout.addWidget(self.keyboard_widget)

    def _connect_handlers(self) -> None:
        self.ui.passwordLineEdit.textChanged.connect(self.change_password_status)
        self.ui.confirmPasswordLineEdit.textChanged.connect(self.change_password_status)

        self.ui.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        self.ui.confirmPasswordHideBtn.clicked.connect(self.hide_unhide_password)

        self.ui.saveButton.clicked.connect(self.handle_save_pwd)
        self.ui.btnLogout.clicked.connect(self.reject)

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code

        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"[ChangePwdDialog] Error: Failed to load translation file: {path}")

    def change_password_status(self) -> None:
        sender = self.sender()
        if sender == self.ui.passwordLineEdit:
            self.ui.errorWidget_1.setVisible(False)
            self.ui.passwordIncorrectLabel.setText("")

        self.ui.errorWidget_2.setVisible(False)

    def hide_unhide_password(self) -> None:
        button: QPushButton = self.sender()
        target_line_edit: Optional[QLineEdit] = None

        if button == self.ui.passwordHideBtn:
            target_line_edit = self.ui.passwordLineEdit
        elif button == self.ui.confirmPasswordHideBtn:
            target_line_edit = self.ui.confirmPasswordLineEdit
        else:
            return

        status = button.property("status")

        if status == "hidden":
            button.setProperty("status", "unhidden")
            target_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            button.setProperty("status", "hidden")
            target_line_edit.setEchoMode(QLineEdit.EchoMode.Password)

        update_element_styles(button)

    def handle_save_pwd(self) -> None:
        password = self.ui.passwordLineEdit.text()
        confirmed_password = self.ui.confirmPasswordLineEdit.text()

        pwd_validator = PasswordValidator()
        if not pwd_validator.validate(password):
            errors = pwd_validator.get_errors().get("password", [])
            error_message = "\n".join(errors)

            self.ui.passwordIncorrectLabel.setText(error_message)
            self.ui.errorWidget_1.setVisible(True)
            print(f"[ChangePwdDialog] Validation failed: {error_message}")
            return

        if password != confirmed_password:
            self.ui.errorWidget_2.setVisible(True)
            print("[ChangePwdDialog] Passwords do not match.")
            return

        hashed_pwd = hash_password(password)
        self.settings_service.owner_password_hash = hashed_pwd

        print("[ChangePwdDialog] Password successfully changed.")
        self.accept()
