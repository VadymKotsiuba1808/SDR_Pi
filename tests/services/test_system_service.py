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
        assert service.os == "Windows", (
            "OS should be Windows when platform.system returns Windows"
        )
        assert service.is_windows is True, "is_windows should be True on Windows"
        assert service.is_linux is False, "is_linux should be False on Windows"

    # Тестуємо для Linux
    with patch("platform.system", return_value="Linux"):
        service = SystemService()
        assert service.os == "Linux", (
            "OS should be Linux when platform.system returns Linux"
        )
        assert service.is_windows is False, "is_windows should be False on Linux"
        assert service.is_linux is True, "is_linux should be True on Linux"


def test_system_service_properties():
    """Тест властивостей версії Python та директорії додатку."""
    service = SystemService()
    assert service.python_version == sys.version, "Python version mismatch"
    assert "app" in service.app_dir or "services" in service.app_dir, (
        f"app_dir '{service.app_dir}' should contain 'app' or 'services'"
    )
