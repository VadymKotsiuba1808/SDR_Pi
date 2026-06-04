"""Тести для головної точки входу (main.py)."""

import asyncio
from typing import Any
from unittest.mock import patch

import qasync
from PyQt6.QtWidgets import QDialog

from main import main


class SafeFuture:
    """
    Обгортка над `asyncio.Future` для безпечного встановлення результату.

    Запобігає виникненню `InvalidStateError`, якщо спробувати встановити
    результат для `Future`, який вже завершений.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        """Ініціалізує об'єкт SafeFuture."""
        self.f = loop.create_future()

    def set_result(self, result: Any) -> None:
        """Встановлює результат, якщо Future ще не завершений."""
        if not self.f.done():
            self.f.set_result(result)

    def __await__(self):
        """Дозволяє використовувати об'єкт в конструкціях await."""
        return self.f.__await__()


class TestMainEntrypoint:
    """
    Тести для перевірки логіки ініціалізації додатку та входу в систему.

    Перевіряє коректність вибору початкового вікна за різних сценаріїв.
    """

    @patch("main.SettingsService")
    @patch("main.SystemService")
    @patch("main.KeyboardService")
    @patch("main.CleanerService")
    @patch("main.LoginDialog")
    @patch("main.MainWindow")
    @patch("main.make_window_stretched")
    @patch("main.enable_auto_scaling")
    def test_main_remember_me_true(
        self,
        mock_auto_scaling,
        mock_stretched,
        mock_main_window_cls,
        mock_login_dlg_cls,
        mock_cleaner_cls,
        mock_keyboard_cls,
        mock_system_cls,
        mock_settings_cls,
        qapp,
    ) -> None:
        """Перевіряє автоматичний вхід при активованій опції 'Запам'ятати мене'."""
        loop = qasync.QEventLoop(qapp)
        asyncio.set_event_loop(loop)

        mock_settings = mock_settings_cls.return_value
        mock_settings.remember_me = True

        mock_cleaner = mock_cleaner_cls.return_value

        with patch("asyncio.Future") as mock_future_cls:
            f_exit = SafeFuture(loop)
            f_exit.set_result(None)
            mock_future_cls.return_value = f_exit

            loop.run_until_complete(main(qapp))

        mock_cleaner.clean_sdr_data.assert_called_once()
        mock_login_dlg_cls.assert_not_called()
        mock_main_window_cls.assert_called_once()
        mock_main_window_cls.return_value.showFullScreen.assert_called_once()
        mock_auto_scaling.assert_called_once_with(mock_main_window_cls.return_value)

    @patch("main.SettingsService")
    @patch("main.SystemService")
    @patch("main.KeyboardService")
    @patch("main.CleanerService")
    @patch("main.LoginDialog")
    @patch("main.MainWindow")
    @patch("main.make_window_stretched")
    @patch("main.enable_auto_scaling")
    def test_main_login_accepted(
        self,
        mock_auto_scaling,
        mock_stretched,
        mock_main_window_cls,
        mock_login_dlg_cls,
        mock_cleaner_cls,
        mock_keyboard_cls,
        mock_system_cls,
        mock_settings_cls,
        qapp,
    ) -> None:
        """Перевіряє перехід до головного вікна після успішної автентифікації."""
        loop = qasync.QEventLoop(qapp)
        asyncio.set_event_loop(loop)

        mock_settings = mock_settings_cls.return_value
        mock_settings.remember_me = False

        mock_login_dlg = mock_login_dlg_cls.return_value

        with patch("asyncio.Future") as mock_future_cls:
            f_exit = SafeFuture(loop)
            f_exit.set_result(None)

            f_dialog = SafeFuture(loop)
            f_dialog.set_result(QDialog.DialogCode.Accepted)

            mock_future_cls.side_effect = [f_exit, f_dialog]

            loop.run_until_complete(main(qapp))

        mock_login_dlg_cls.assert_called_once()
        mock_login_dlg.showFullScreen.assert_called_once()
        mock_stretched.assert_called_once_with(mock_login_dlg)

        mock_main_window_cls.assert_called_once()
        mock_main_window_cls.return_value.showFullScreen.assert_called_once()

    @patch("main.SettingsService")
    @patch("main.SystemService")
    @patch("main.KeyboardService")
    @patch("main.CleanerService")
    @patch("main.LoginDialog")
    @patch("main.MainWindow")
    @patch("main.make_window_stretched")
    @patch("main.enable_auto_scaling")
    def test_main_login_rejected(
        self,
        mock_auto_scaling,
        mock_stretched,
        mock_main_window_cls,
        mock_login_dlg_cls,
        mock_cleaner_cls,
        mock_keyboard_cls,
        mock_system_cls,
        mock_settings_cls,
        qapp,
    ) -> None:
        """Перевіряє завершення програми при відхиленні входу."""
        loop = qasync.QEventLoop(qapp)
        asyncio.set_event_loop(loop)

        mock_settings = mock_settings_cls.return_value
        mock_settings.remember_me = False

        with patch("asyncio.Future") as mock_future_cls:
            f_exit = SafeFuture(loop)
            f_dialog = SafeFuture(loop)
            f_dialog.set_result(QDialog.DialogCode.Rejected)

            mock_future_cls.side_effect = [f_exit, f_dialog]

            with patch.object(qapp, "quit") as mock_quit:
                loop.run_until_complete(main(qapp))

                mock_login_dlg_cls.assert_called_once()
                mock_main_window_cls.assert_not_called()
                mock_quit.assert_called_once()
