"""
Загальні фікстури для налаштування середовища наскрізного (E2E) тестування.

Цей модуль містить глобальні перехоплення (patches) системних модулів,
налаштування ізольованої конфігурації та управління життєвим циклом
тестового сервера та клієнтських сервісів.
"""

import os
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from app.models.object_class import ObjectClass
from app.services.keyboard_service import KeyboardService
from app.services.settings_service import SettingsService
from app.services.system_service import SystemService
from pi_server.database_service import DatabaseService
from pi_server.pi_server_service import PiServerService


@pytest.fixture(scope="session", autouse=True)
def mock_os_modules() -> Generator[None, None, None]:
    """Глобально замінює системні модулі на заглушки."""
    os.environ["SDR_PI_TESTING"] = "1"

    with (
        patch.dict(
            "sys.modules",
            {
                "keyboard": MagicMock(),
                "win32api": MagicMock(),
                "win32gui": MagicMock(),
                "pynput": MagicMock(),
                "pynput.keyboard": MagicMock(),
            },
        ),
        patch("app.widgets.main_window.restart_process", MagicMock()),
        patch("app.widgets.settings_dialog.restart_process", MagicMock()),
    ):
        yield


@pytest.fixture(autouse=True)
def close_all_windows() -> Generator[None, None, None]:
    """Закриває всі активні вікна після кожного тесту."""
    yield
    for widget in QApplication.topLevelWidgets():
        widget.close()


class E2ESettings(SettingsService):
    """
    Спеціалізована реалізація налаштувань для E2E тестів.

    !!! note "Ізоляція"
        Використовує тимчасовий шлях для файлу конфігурації, щоб запобігти зміні
        користувацьких налаштувань розробника під час виконання тестів.
    """

    def __init__(self, config_path: Path) -> None:
        """Ініціалізує налаштування тестовими значеннями."""
        super().__init__(config_path=config_path)

        self.pi_target_ip = "127.0.0.1"
        self.pi_target_port = 0
        self.remember_me = False
        self.role = "operator"
        self.owner_password_hash = ""
        self.lang_code = "uk"


@pytest.fixture
def e2e_server() -> Generator[PiServerService, None, None]:
    """Запускає екземпляр PiServerService в ізольованій базі даних."""
    db = DatabaseService(db_url="sqlite:///:memory:")
    # Мінімальний набір даних для функціонування інтерфейсу
    db.add_class(ObjectClass(id=None, name="UAV"))
    db.add_class(ObjectClass(id=None, name="BIRD"))

    srv = PiServerService(port=0, db_service=db)
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture
def app_services(e2e_server: PiServerService, tmp_path: Path) -> Dict[str, Any]:
    """Створює та налаштовує клієнтські сервіси для тестування."""
    test_config_path = tmp_path / "e2e_config.ini"

    settings = E2ESettings(test_config_path)
    assert e2e_server.server is not None, "Сервер має бути ініціалізований"
    settings.pi_target_port = e2e_server.server.serverPort()

    system = SystemService()
    keyboard = KeyboardService(system)

    return {"settings": settings, "system": system, "keyboard": keyboard}
