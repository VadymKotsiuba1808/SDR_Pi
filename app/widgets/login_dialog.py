from PyQt6.QtWidgets import QDialog
from PyQt6 import uic

from app.services.settings_service import SettingsService
from app.utils.password_utils import  verify_password

class LoginDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings

        remember_me=self.settings_service.remember_me
        if(remember_me):
            self.isAlreadyAccept=True
        else: 
            self.isAlreadyAccept=False
        
        uic.loadUi("app/ui/login_dialog.ui", self) 

        role=self.settings_service.role

        self.roleComboBox.currentIndexChanged.connect(self.toggle_password_field)
        self.roleComboBox.setCurrentIndex(0 if role=="operator"  else 1 )  
        self.passwordLineEdit.textChanged.connect(self.change_password_status)
        
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

    def handle_login(self):
        role = self.roleComboBox.currentText()
        
        if role == "Оператор":
            self.settings_service.role="operator"
            self.accept() 

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
                self.accept() 
            else:
                # Пароль неправильний!
                self.passwordIncorrectLabel.setVisible(True)

