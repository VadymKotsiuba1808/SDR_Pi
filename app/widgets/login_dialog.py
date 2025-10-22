from PyQt6.QtWidgets import QDialog, QLineEdit
from PyQt6 import uic

from app.services.settings_service import SettingsService
from app.utils.password_utils import  verify_password

class LoginDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings
        
        uic.loadUi("app/ui/login_dialog.ui", self) 

        role=self.settings_service.role

        self.roleComboBox.currentIndexChanged.connect(self.toggle_password_field)
        self.roleComboBox.setCurrentIndex(0 if role=="operator"  else 1 )  
        self.passwordLineEdit.textChanged.connect(self.change_password_status)

        self.passwordHideBtn.clicked.connect(self.hide_unhide_password)
        
        self.loginButton.clicked.connect(self.handle_login)


    def toggle_password_field(self):
        """
        Показує або ховає контейнер з паролем 
        залежно від обраної ролі.
        """
        current_role = self.roleComboBox.currentText()
        
        if current_role == "Власник":
            self.passwordContainer.setVisible(True)
        else: 
            self.passwordContainer.setVisible(False)
    
    def change_password_status(self):
        #Приховую Label зі статусом

        self.passwordIncorrectLabel.setVisible(False)

    def hide_unhide_password(self):
        status=self.passwordHideBtn.property("status")
        print("Status:",status)
        if(status=="hidden"):
            self.passwordHideBtn.setProperty("status","unhidden")
            self.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.passwordHideBtn.setProperty("status","hidden")
            self.passwordLineEdit.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.passwordHideBtn.style().unpolish(self.passwordHideBtn)
        self.passwordHideBtn.style().polish(self.passwordHideBtn)
        self.passwordHideBtn.update()


    def handle_login(self):
        role = self.roleComboBox.currentText()
        
        if role == "Оператор":
            self.settings_service.role="operator"
            self.accept_window()

            return 

        # 2. Логіка для Власника (потрібна перевірка пароля)
        if role == "Власник":

            password = self.passwordLineEdit.text()
            real_password=self.settings_service.owner_password_hash
            
            is_password_correct = verify_password(password,real_password) 
            
            if is_password_correct:
                # Пароль правильний!
                remember = self.rememberCheckBox.isChecked()
                if(remember):
                    self.settings_service.remember_me=remember
                

                self.settings_service.role="owner"
                self.accept_window()
            else:
                # Пароль неправильний!
                self.passwordIncorrectLabel.setVisible(True)

    def accept_window(self):
        # self.hide()
        self.finished.emit(QDialog.DialogCode.Accepted)

