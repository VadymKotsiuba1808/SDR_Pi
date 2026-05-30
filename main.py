"""
Головна точка входу в програму.
Ініціалізує QApplication, та запускає авторизацію і головне вікно (MainWindow).
"""

import asyncio
import sys

import qasync
from PyQt6.QtWidgets import QApplication, QDialog

from app.services.cleaner_service import CleanerService
from app.services.keyboard_service import KeyboardService
from app.services.settings_service import SettingsService
from app.services.system_service import SystemService
from app.utils.async_utils import make_safe_set_result
from app.widgets.autosize_window import (
    enable_auto_scaling,
    make_window_stretched,
)
from app.widgets.login_dialog import LoginDialog
from app.widgets.main_window import MainWindow


async def main():
    app = QApplication.instance()

    settings_service = SettingsService()
    system_service = SystemService()
    keyboard_service = KeyboardService(system_service)

    clean_service = CleanerService(settings_service)
    clean_service.clean_sdr_data()

    future = asyncio.Future()
    # Коректне закриття при виході з програми
    app.aboutToQuit.connect(lambda: future.set_result(None))
    remember_me = settings_service.remember_me

    result_code = None

    if not remember_me:
        # Вимикаємо автоматичне завершення програми після закриття останнього вікна
        app.setQuitOnLastWindowClosed(False)
        login_dialog = LoginDialog(settings=settings_service, keyboard=keyboard_service)
        make_window_stretched(login_dialog)

        dialog_finished_future = asyncio.Future()

        login_dialog.finished.connect(make_safe_set_result(dialog_finished_future))

        login_dialog.showFullScreen()

        result_code = await dialog_finished_future

    if (
        result_code == QDialog.DialogCode.Accepted or remember_me
    ):  # .Accepted це зазвичай 1
        app.setQuitOnLastWindowClosed(True)
        window = MainWindow(
            settings=settings_service, keyboard=keyboard_service, system=system_service
        )

        enable_auto_scaling(window)
        window.showFullScreen()

        if not remember_me:
            await asyncio.sleep(0.05)
            login_dialog.close()

        await future

    else:
        if app is not None:
            app.quit()


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        loop.run_until_complete(main())

    except asyncio.CancelledError:
        sys.exit(0)
