import sys
import asyncio
import qasync
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow

from app.widgets.main_window import MainWindow
from app.widgets.login_dialog import LoginDialog
from app.services.settings_service import SettingsService
from app.widgets.scalable_window import make_scalable

async def main():
    app = QApplication.instance()
    # Вимикаємо автоматичне завершення програми після закриття останнього вікна
    
    settings_service = SettingsService()
    
    future = asyncio.Future()
    # Коректне закриття при виході з програми
    app.aboutToQuit.connect(lambda: future.set_result(None))
    remember_me=settings_service.remember_me
    
    if(remember_me==False):
        app.setQuitOnLastWindowClosed(False)
        login_dialog = LoginDialog(settings=settings_service)
        # Створюємо "Future", який буде "чекати" на закриття діалогу
        dialog_finished_future = asyncio.Future()
        # Під'єднуємо сигнал 'finished' (який спрацює при .accept() або .reject())
        # до нашого future.
        login_dialog.finished.connect(dialog_finished_future.set_result)
        
        login_dialog.showFullScreen()
        
        result_code = await dialog_finished_future
    
    if (result_code == QDialog.DialogCode.Accepted or 
        remember_me==True):  # .Accepted це зазвичай 1
        
        app.setQuitOnLastWindowClosed(True)
        window = MainWindow(settings=settings_service)
        ScalableMainWindow = make_scalable(QMainWindow)
        scalable_window = ScalableMainWindow(widget=window)
        scalable_window.showFullScreen()

        await future
        
    else:
        app.quit()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        loop.run_until_complete(main())
        
    except asyncio.CancelledError:
        sys.exit(0)