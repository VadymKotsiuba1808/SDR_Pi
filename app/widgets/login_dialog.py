from PyQt6.QtWidgets import QDialog
from PyQt6 import uic

from app.services.settings_service import SettingsService
from app.widgets.main_window import MainWindow
from app.widgets.scalable_window import ScalableWindow

class LoginDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings
        
        uic.loadUi("app/ui/login_dialog.ui", self) 

        # Знаходимо потрібні віджети за іменами, які ми вказали в .ui
        # (Якщо використовуєш авто-генерацію, вони можуть бути вже в self)
        # self.roleComboBox
        # self.passwordContainer
        # self.loginButton

        self.roleComboBox.currentIndexChanged.connect(self.toggle_password_field)
        
        self.loginButton.clicked.connect(self.handle_login)
        
        self.toggle_password_field()

    def toggle_password_field(self):
        """
        Показує або ховає контейнер з паролем 
        залежно від обраної ролі.
        """
        current_role = self.roleComboBox.currentText()
        
        if current_role == "Власник":
            self.passwordContainer.setVisible(True)
        else: # Для "Оператор"
            self.passwordContainer.setVisible(False)
            
    def handle_login(self):
        role = self.roleComboBox.currentText()
        
        # 1. Логіка для Оператора (вхід без пароля)
        if role == "Оператор":
            # Логін успішний, закриваємо діалог з результатом "OK"
            self.accept() 

            return # Виходимо з функції

        # 2. Логіка для Власника (потрібна перевірка пароля)
        if role == "Власник":
            password = self.passwordLineEdit.text()
            
            # ... тут ваша реальна логіка перевірки пароля ...
            # Наприклад:
            is_password_correct = (password == "mypassword123") 
            
            if is_password_correct:
                # Пароль правильний!
                remember = self.rememberCheckBox.isChecked()
                # (Тут можна зберегти 'remember' у self.settings_service)
                
                # Логін успішний, закриваємо діалог з результатом "OK"
                
                self.accept() 
            else:
                # Пароль неправильний!
                print("Неправильний пароль!")
                # НЕ закривайте вікно (не викликайте self.reject()).
                # Просто дайте користувачу спробувати ще раз.
                # (Можна додати червоний QLabel з помилкою)
                pass
