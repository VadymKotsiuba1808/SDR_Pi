"""
Тести для системного сервісу (SystemService).
"""

import sys
from unittest.mock import patch

from app.services.system_service import SystemService


def test_system_service_initialization():
    """Тест ініціалізації SystemService та визначення ОС."""
    # Тестуємо для Windows
    with patch("platform.system", return_value="Windows"):
        service = SystemService()
        assert service.os == "Windows"
        assert service.is_windows is True
        assert service.is_linux is False

    # Тестуємо для Linux
    with patch("platform.system", return_value="Linux"):
        service = SystemService()
        assert service.os == "Linux"
        assert service.is_windows is False
        assert service.is_linux is True


def test_system_service_properties():
    """Тест властивостей версії Python та директорії додатку."""
    service = SystemService()
    assert service.python_version == sys.version
    assert "app" in service.app_dir or "services" in service.app_dir
