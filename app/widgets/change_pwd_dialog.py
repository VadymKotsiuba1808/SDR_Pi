from PyQt6.QtWidgets import QDialog, QLineEdit
from PyQt6.QtCore import QCoreApplication, QEvent, QTranslator

from PyQt6 import uic

from app.ui.ui_change_pwd_dialog import Ui_ChangePwdDialog

from app.protocols import ChangePwdDialogSettings
from app.utils.password_utils import hash_password
from app.validators.password_validator import PasswordValidator
from app.utils.ui_utils import update_element_styles


class ChangePwdDialog(QDialog):
    def __init__(self, settings: ChangePwdDialogSettings, parent=None):
        super().__init__(parent)

        self.settings_service = settings

        self._load_ui()
        print("[ChangePwdDialog] Інтерфейс завантажено.")

        self._setup_state_variables()

        self._connect_handlers()
        print("[ChangePwdDialog] Сигнали підключено.")

        self._load_language()

    def changeEvent(self, event):
        # Ловимо подію, яку надіслав installTranslator
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("Зміна мови, оновлюю UI...")
                # Викликаємо авто-згенеровану функцію
                self.ui.retranslateUi(self)
        else:
            # Передаємо всі інші події (натискання клавіш, зміна розміру тощо)
            # на стандартну обробку
            super().changeEvent(event)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_ChangePwdDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/change_pwd_dialog.ui", self)
            self.ui = self

    def _setup_state_variables(self):
        self.translator = QTranslator()

    def _connect_handlers(self):
        self.ui.passwordLineEdit.textChanged.connect(self.change_password_status)
        self.ui.confirmPasswordLineEdit.textChanged.connect(self.change_password_status)

        self.ui.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        self.ui.confirmPasswordHideBtn.clicked.connect(self.hide_unhide_password)

        self.ui.saveButton.clicked.connect(self.handle_save_pwd)

    def _load_language(self):
        # Видаляємо старий перекладач
        lang_code = self.settings_service.lang_code

        if lang_code == None:
            return

        QCoreApplication.removeTranslator(self.translator)

        # Завантажуємо та встановлюємо новий
        path = f"app/i18n/qm/app_{lang_code}.qm"  # Перевірте правильність шляху
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    def change_password_status(self):
        # Приховую Label зі статусом

        if self.sender() == self.ui.passwordLineEdit:
            self.ui.errorWidget_1.setVisible(False)
            self.ui.passwordIncorrectLabel.setText("")

        print(
            "[change_password_status] Зміна тексту в полі пароля — ховаємо мітку помилки."
        )
        self.ui.errorWidget_2.setVisible(False)

    def hide_unhide_password(self):
        button = self.sender()
        target_line_edit = None

        if button == self.ui.passwordHideBtn:
            target_line_edit = self.ui.passwordLineEdit
        elif button == self.ui.confirmPasswordHideBtn:
            target_line_edit = self.ui.confirmPasswordLineEdit
        else:
            return

        status = button.property("status")
        print(f"[hide_unhide_password] Поточний статус: {status}")

        if status == "hidden":
            print("[hide_unhide_password] Відображаємо пароль.")
            button.setProperty("status", "unhidden")
            target_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            print("[hide_unhide_password] Приховуємо пароль.")
            button.setProperty("status", "hidden")
            target_line_edit.setEchoMode(QLineEdit.EchoMode.Password)

        update_element_styles(button)
        print("[hide_unhide_password] Оновлення стилю завершено.")

    def handle_save_pwd(self):

        password = self.ui.passwordLineEdit.text()

        pwd_validator = PasswordValidator()

        if pwd_validator.validate(password) == False:
            error_message = "\n".join(pwd_validator.get_errors()["password"])
            self.ui.passwordIncorrectLabel.setText(error_message)
            self.ui.errorWidget_1.setVisible(True)
            print("[handle_change_pwd] Пароль не валідний.")
            return

        confirmedPassword = self.ui.confirmPasswordLineEdit.text()

        if password != confirmedPassword:
            self.ui.errorWidget_2.setVisible(True)
            print("[handle_change_pwd] Паролі не співпадають.")
            return

        hashed_pwd = hash_password(password)
        self.settings_service.owner_password_hash = hashed_pwd

        print("[handle_change_pwd] Успішна зміна паролю.")

        self.accept_window()

    def accept_window(self):
        print("[accept_window] Закриття діалогу з кодом Accepted.")
        self.accept()
