# main.py
import os
import sys
import asyncio
import qasync
from PyQt6.QtWidgets import QApplication
from screeninfo import get_monitors

# Ваші класи
from app.main_window import MainWindow
from app.services.settings_service import SettingsService


# async def main():
#     # 1️⃣ Масштабування за розміром екрана
#     try:
#         primary_monitor = next(m for m in get_monitors() if m.is_primary)
#         screen_width = primary_monitor.width
#         base_width = 1920.0
#         if screen_width < base_width:
#             scale_factor = screen_width / base_width
#             os.environ["QT_SCALE_FACTOR"] = str(scale_factor)
#     except Exception as e:
#         print(f"Не вдалося визначити розмір екрана: {e}")

#     # 2️⃣ Створюємо Qt-додаток
#     app = QApplication(sys.argv)

#     # 3️⃣ Ініціалізація сервісів і головного вікна
#     settings_service = SettingsService()
#     window = MainWindow(settings=settings_service)
#     window.showFullScreen()

#     # 4️⃣ Чекаємо поки програма не завершиться (Qt закриє події)
#     try:
#         await asyncio.Future()  # програма живе, доки не закриєш вікно
#     except asyncio.CancelledError:
#         print("Програма завершується...")


# if __name__ == '__main__':
#     try:
#         qasync.run(main())
#     except KeyboardInterrupt:
#         print("Примусове завершення (Ctrl+C).")

async def main():
    # Ця функція тепер простіша, оскільки задача запускається з вікна
    future = asyncio.Future()
    app = QApplication.instance()
    
    # Коректне закриття при виході з програми
    app.aboutToQuit.connect(lambda: future.set_result(None))

    settings_service = SettingsService()
    window = MainWindow(settings=settings_service)
    window.showFullScreen()
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