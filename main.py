import sys
import asyncio
import qasync
from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.services.settings_service import SettingsService
from app.widgets.scalable_window import ScalableWindow

async def main():

    future = asyncio.Future()
    app = QApplication.instance()
    
    # Коректне закриття при виході з програми
    app.aboutToQuit.connect(lambda: future.set_result(None))

    settings_service = SettingsService()
    window = MainWindow(settings=settings_service)
    scalable_window = ScalableWindow(window)
    scalable_window.showFullScreen()
    await future
    return True

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        sys.exit(loop.run_until_complete(main()))
        
    except asyncio.CancelledError:
        sys.exit(0)