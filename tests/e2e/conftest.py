"""
Загальні фікстури для E2E тестів.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.object_class import ObjectClass
from app.services.keyboard_service import KeyboardService
from app.services.settings_service import SettingsService
from app.services.system_service import SystemService
from pi_server.database_service import DatabaseService
from pi_server.pi_server_service import PiServerService


# Глобальний патч для системних модулів до будь-яких імпортів сервісів
@pytest.fixture(scope="session", autouse=True)
def mock_os_modules():
    # Встановлюємо прапор тестування для згортання вікон
    os.environ["SDR_PI_TESTING"] = "1"

    with patch.dict(
        "sys.modules",
        {
            "keyboard": MagicMock(),
            "win32api": MagicMock(),
            "win32gui": MagicMock(),
            "pynput": MagicMock(),
            "pynput.keyboard": MagicMock(),
        },
    ):
        yield


class E2ESettings(SettingsService):
    """Налаштування для E2E тестів, щоб не змінювати реальний config.ini."""

    def __init__(self, config_path: Path):
        # Передаємо шлях до тимчасового файлу в базовий клас
        super().__init__(config_path=config_path)

        # Встановлюємо значення за замовчуванням для тестів
        self.pi_target_ip = "127.0.0.1"
        self.pi_target_port = 0  # Буде встановлено динамічно в app_services
        self.remember_me = False
        self.role = "operator"
        self.owner_password_hash = ""
        self.lang_code = "uk"


@pytest.fixture
def e2e_server():
    """Фікстура для запуску реального Pi сервера."""
    db = DatabaseService(db_url="sqlite:///:memory:")
    # Початкове наповнення бази
    db.add_class(ObjectClass(id=None, name="UAV"))
    db.add_class(ObjectClass(id=None, name="BIRD"))

    srv = PiServerService(port=0, db_service=db)
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture
def app_services(e2e_server, tmp_path):
    """Фікстура для ініціалізації клієнтських сервісів."""
    # Створюємо тимчасовий файл конфігурації для кожного тесту
    test_config_path = tmp_path / "e2e_config.ini"

    settings = E2ESettings(test_config_path)
    settings.pi_target_port = e2e_server.server.serverPort()

    system = SystemService()
    keyboard = KeyboardService(system)

    return {"settings": settings, "system": system, "keyboard": keyboard}
