"""
Тести для сервісу налаштувань.
"""

from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings

from app.core.constants import CLEAN_TARGET_NAME
from app.models.settings import CleanRule
from app.services.settings_service import SettingsService


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """
    Фікстура для створення тимчасового файлу конфігурації.
    """
    config_file = tmp_path / "test_config.ini"
    return config_file


@pytest.fixture
def settings_service(temp_config: Path) -> SettingsService:
    """
    Фікстура для ініціалізації SettingsService з тимчасовим файлом.
    """
    return SettingsService(config_path=temp_config)


def test_initial_defaults(settings_service: SettingsService) -> None:
    """
    Тест значень за замовчуванням.
    """
    assert settings_service.pi_target_ip == "0.0.0.0"
    assert settings_service.pi_target_port == 6000
    assert settings_service.role == "operator"
    assert settings_service.remember_me is False


def test_set_and_save(settings_service: SettingsService, temp_config: Path) -> None:
    """
    Тест збереження налаштувань у файл.
    """
    new_ip = "192.168.1.100"
    settings_service.pi_target_ip = new_ip
    settings_service.sync()

    # Створюємо новий екземпляр, щоб перевірити, чи зчитаються дані з файлу
    new_service = SettingsService(config_path=temp_config)
    assert new_service.pi_target_ip == new_ip


def test_settings_changed_signal(settings_service: SettingsService, qtbot) -> None:
    """
    Тест виклику сигналу при зміні налаштувань.
    """
    with qtbot.waitSignal(settings_service.settings_changed, timeout=1000):
        settings_service.pi_target_port = 8080


def test_complex_types_list(
    settings_service: SettingsService, temp_config: Path
) -> None:
    """
    Тест обробки списків (radio_range_mhz).
    """
    new_range = [200, 800]
    settings_service.radio_range_mhz = new_range
    settings_service.sync()

    new_service = SettingsService(config_path=temp_config)
    # QSettings може повертати список рядків або цілих чисел залежно від того, як він зберігся.
    # SettingsService має це обробляти, але давайте перевіримо значення.
    assert list(new_service.radio_range_mhz) == new_range


def test_complex_types_dict_clean_settings(
    settings_service: SettingsService, temp_config: Path
) -> None:
    """
    Тест обробки складного словника (clean_settings).
    """
    clean_rule = CleanRule(enabled=True, days=30)
    settings_service.clean_settings = {CLEAN_TARGET_NAME.LOGS: clean_rule}
    settings_service.sync()

    new_service = SettingsService(config_path=temp_config)
    assert CLEAN_TARGET_NAME.LOGS in new_service.clean_settings
    assert new_service.clean_settings[CLEAN_TARGET_NAME.LOGS].enabled is True
    assert new_service.clean_settings[CLEAN_TARGET_NAME.LOGS].days == 30


def test_reload_from_file(
    settings_service: SettingsService, temp_config: Path, qtbot
) -> None:
    """
    Тест перезавантаження налаштувань при зміні файлу ззовні.
    """
    # Змінюємо файл через QSettings напряму (імітація зовнішньої зміни)
    external_settings = QSettings(str(temp_config), QSettings.Format.IniFormat)
    external_settings.setValue("auth/role", "owner")
    external_settings.sync()

    # Оскільки QFileSystemWatcher працює асинхронно, чекаємо сигналу або вручну викликаємо reload
    # Для надійності тесту викликаємо метод безпосередньо, але перевіряємо, що сигнал теж працює
    with qtbot.waitSignal(settings_service.settings_changed, timeout=2000):
        settings_service._reload_from_file()

    assert settings_service.role == "owner"
