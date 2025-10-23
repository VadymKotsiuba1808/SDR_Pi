from PyQt6.QtWidgets import QDialog, QLineEdit
from PyQt6 import uic

from app.services.settings_service import SettingsService
from app.utils.password_utils import hash_password

class ChangePwdDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)

        self.settings_service = settings
        
        uic.loadUi("app/ui/change_pwd_dialog.ui", self) 

        self.passwordLineEdit.textChanged.connect(self.change_password_status)
        self.confirmPasswordLineEdit.textChanged.connect(self.change_password_status)

        self.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        self.confirmPasswordHideBtn.clicked.connect(self.hide_unhide_password)
        
        self.saveButton.clicked.connect(self.handle_save_pwd)
        print("[ChangePwdDialog] Сигнали підключено.")

    
    def change_password_status(self):
        # Приховую Label зі статусом
        print("[change_password_status] Зміна тексту в полі пароля — ховаємо мітку помилки.")
        self.passwordIncorrectLabel.setVisible(False)

    def hide_unhide_password(self):
        
        button=self.sender()
        target_line_edit=None
        
        if(button==self.passwordHideBtn):
            target_line_edit=self.passwordLineEdit
        elif(button==self.confirmPasswordHideBtn):
            target_line_edit=self.confirmPasswordLineEdit
        else: return
            
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
        
        password = self.passwordLineEdit.text()
        confirmedPassword=self.confirmPasswordLineEdit.text()
        
        if(password!=confirmedPassword):
            self.passwordIncorrectLabel.setVisible(True)
            print("[handle_change_pwd] Паролі не співпадають.")
            return
        
        hashed_pwd=hash_password(password)
        self.settings_service.owner_password_hash=hashed_pwd
        
        print("[handle_change_pwd] Успішна зміна паролю.")
        
        self.accept_window()

    def accept_window(self):
        print("[accept_window] Закриття діалогу з кодом Accepted.")
        self.accept()
