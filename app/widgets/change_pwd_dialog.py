from PyQt6.QtWidgets import QDialog, QLineEdit
from PyQt6.QtCore import QCoreApplication, QEvent, QTranslator

# from PyQt6 import uic

from app.ui.ui_change_pwd_dialog import Ui_ChangePwdDialog

from app.protocols import ChangePwdDialogSettings
from app.utils.password_utils import hash_password


class ChangePwdDialog(QDialog):
    def __init__(self, settings: ChangePwdDialogSettings, parent=None):
        super().__init__(parent)

        self.settings_service = settings

        # uic.loadUi("app/ui/change_pwd_dialog.ui", self)
        self.ui = Ui_ChangePwdDialog()
        self.ui.setupUi(self)

        self.ui.passwordLineEdit.textChanged.connect(self.change_password_status)
        self.ui.confirmPasswordLineEdit.textChanged.connect(self.change_password_status)

        self.ui.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        self.ui.confirmPasswordHideBtn.clicked.connect(self.hide_unhide_password)

        self.ui.saveButton.clicked.connect(self.handle_save_pwd)

        self.translator = QTranslator()

        self.load_language()

        print("[ChangePwdDialog] Сигнали підключено.")

    def changeEvent(self, event):
        # Ловимо подію, яку надіслав installTranslator
        if event.type() == QEvent.Type.LanguageChange:
            print("Зміна мови, оновлюю UI...")
            # Викликаємо авто-згенеровану функцію
            self.ui.retranslateUi(self)
        else:
            # Передаємо всі інші події (натискання клавіш, зміна розміру тощо)
            # на стандартну обробку
            super().changeEvent(event)

    def load_language(self):
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
        print(
            "[change_password_status] Зміна тексту в полі пароля — ховаємо мітку помилки."
        )
        self.ui.passwordIncorrectLabel.setVisible(False)

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

        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
        print("[hide_unhide_password] Оновлення стилю завершено.")

    def handle_save_pwd(self):

        password = self.ui.passwordLineEdit.text()
        confirmedPassword = self.ui.confirmPasswordLineEdit.text()

        if password != confirmedPassword:
            self.ui.passwordIncorrectLabel.setVisible(True)
            print("[handle_change_pwd] Паролі не співпадають.")
            return

        hashed_pwd = hash_password(password)
        self.settings_service.owner_password_hash = hashed_pwd

        print("[handle_change_pwd] Успішна зміна паролю.")

        self.accept_window()

    def accept_window(self):
        print("[accept_window] Закриття діалогу з кодом Accepted.")
        self.accept()
