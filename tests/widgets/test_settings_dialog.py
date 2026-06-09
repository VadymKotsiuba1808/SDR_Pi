"""
Тести для діалогу налаштувань.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QDialog

from app.core.constants import CLEAN_TARGET_NAME
from app.models.settings import CleanRule
from app.widgets.settings_dialog import SettingsDialog


@pytest.fixture
def mock_settings():
    """Фікстура для макета налаштувань."""
    settings = MagicMock()
    settings.radar_max_radius_km = 100.0
    settings.gps_interval_s = 60
    settings.main_relays = ["K1"]
    settings.detection_ttl_s = 5
    settings.is_jammer_auto_start_enabled = True
    settings.is_jammer_auto_stop_enabled = False
    settings.jammer_auto_stop_interval_s = 600
    settings.clean_settings = {CLEAN_TARGET_NAME.LOGS: CleanRule(enabled=True, days=30)}
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def settings_dialog(qtbot, mock_settings):
    """Фікстура для ініціалізації SettingsDialog."""
    dialog = SettingsDialog(mock_settings)
    qtbot.addWidget(dialog)
    yield dialog
    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.removeTranslator(dialog.translator)


def test_ui_initialization_with_settings(settings_dialog, mock_settings):
    """Тест ініціалізації UI значеннями з сервісу."""
    assert settings_dialog.ui.inpMaxRadius.value() == 100.0
    assert settings_dialog.ui.inpGpsInterval.value() == 60
    assert settings_dialog.ui.chkJammerAutoStart.isChecked() is True
    assert settings_dialog.ui.chkJammerAutoStop.isChecked() is False
    assert settings_dialog.ui.inpJammerStopInterval.isEnabled() is False


def test_jammer_auto_stop_toggle(settings_dialog, qtbot):
    """Тест активації поля інтервалу при ввімкненні автостопу."""
    qtbot.mouseClick(
        settings_dialog.ui.chkJammerAutoStop,
        pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
    )
    assert settings_dialog.ui.chkJammerAutoStop.isChecked() is True
    assert settings_dialog.ui.inpJammerStopInterval.isEnabled() is True


def test_clean_settings_buffering(settings_dialog, qtbot):
    """Тест буферизації налаштувань очистки."""
    # Обираємо логи (вони мають бути ввімкнені за замовчуванням у нашому моку)
    settings_dialog.ui.cmbCleanTarget.setCurrentIndex(0)
    assert settings_dialog.ui.chkCleanEnabled.isChecked() is True
    assert settings_dialog.ui.inpCleanDays.value() == 30

    # Змінюємо значення
    qtbot.mouseClick(
        settings_dialog.ui.chkCleanEnabled,
        pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
    )
    settings_dialog.ui.inpCleanDays.setValue(45)

    # Перемикаємося на інший таргет
    settings_dialog.ui.cmbCleanTarget.setCurrentIndex(1)
    # Має бути вимкнено за замовчуванням (не було в моку)
    assert settings_dialog.ui.chkCleanEnabled.isChecked() is False

    # Повертаємося до логів
    settings_dialog.ui.cmbCleanTarget.setCurrentIndex(0)
    assert settings_dialog.ui.chkCleanEnabled.isChecked() is False
    assert settings_dialog.ui.inpCleanDays.value() == 45


def test_save_settings(settings_dialog, qtbot):
    """Тест збереження налаштувань."""
    settings_dialog.ui.inpMaxRadius.setValue(250.0)
    settings_dialog.ui.inpGpsInterval.setValue(30)

    with qtbot.waitSignal(settings_dialog.finished, timeout=1000) as blocker:
        qtbot.mouseClick(
            settings_dialog.ui.btnSave,
            pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
        )

    assert blocker.args == [QDialog.DialogCode.Accepted]
    new_data = settings_dialog.get_settings()
    assert new_data.radar_max_radius_km == 250.0
    assert new_data.gps_interval_s == 30


def test_restart_app_logout(settings_dialog, mock_settings, qtbot):
    """Тест виходу з системи (рестарт процесу)."""
    with patch("app.widgets.settings_dialog.restart_process") as mock_restart:
        qtbot.mouseClick(
            settings_dialog.ui.btnLogout,
            pytest.importorskip("PyQt6.QtCore").Qt.MouseButton.LeftButton,
        )

        assert mock_settings.remember_me is False
        assert mock_restart.called
