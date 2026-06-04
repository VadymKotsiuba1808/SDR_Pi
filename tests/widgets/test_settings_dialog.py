"""Модуль для тестування діалогу налаштувань."""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QDialog

from app.core.constants import CLEAN_TARGET_NAME
from app.models.settings import CleanRule
from app.protocols import SettingsDialogSettings
from app.widgets.settings_dialog import SettingsData, SettingsDialog


@pytest.fixture
def mock_settings() -> MagicMock:
    """Створює макет об'єкта налаштувань для тестів."""
    settings = MagicMock(spec=SettingsDialogSettings)
    settings.radar_max_radius_km = 100.0
    settings.gps_interval_s = 60
    settings.main_relays = ["K1"]
    settings.detection_ttl_s = 5
    settings.is_jammer_auto_start_enabled = True
    settings.is_jammer_auto_stop_enabled = False
    settings.jammer_auto_stop_interval_s = 600
    settings.clean_settings = {CLEAN_TARGET_NAME.LOGS: CleanRule(enabled=True, days=30)}
    settings.lang_code = "uk"
    settings.remember_me = True
    return settings


@pytest.fixture
def settings_dialog(qtbot, mock_settings: MagicMock):
    """Ініціалізує екземпляр SettingsDialog для тестування."""
    dialog = SettingsDialog(mock_settings)
    qtbot.addWidget(dialog)
    yield dialog

    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.removeTranslator(dialog.translator)


def test_ui_initialization_with_settings(
    settings_dialog: SettingsDialog, mock_settings: MagicMock
) -> None:
    """Перевіряє коректність заповнення полів UI."""
    assert settings_dialog.ui.inpMaxRadius.value() == 100.0, "Radar radius mismatch"
    assert settings_dialog.ui.inpGpsInterval.value() == 60, "GPS interval mismatch"
    assert settings_dialog.ui.chkJammerAutoStart.isChecked() is True, (
        "Jammer auto-start status is incorrect"
    )
    assert settings_dialog.ui.chkJammerAutoStop.isChecked() is False, (
        "Jammer auto-stop status is incorrect"
    )
    assert settings_dialog.ui.inpJammerStopInterval.isEnabled() is False


def test_jammer_auto_stop_toggle(settings_dialog: SettingsDialog, qtbot) -> None:
    """Перевіряє динамічну зміну доступності полів."""
    from PyQt6.QtCore import Qt

    qtbot.mouseClick(settings_dialog.ui.chkJammerAutoStop, Qt.MouseButton.LeftButton)

    assert settings_dialog.ui.chkJammerAutoStop.isChecked() is True
    assert settings_dialog.ui.inpJammerStopInterval.isEnabled() is True


def test_clean_settings_buffering(settings_dialog: SettingsDialog, qtbot) -> None:
    """Перевіряє механізм тимчасового збереження налаштувань очищення."""
    from PyQt6.QtCore import Qt

    settings_dialog.ui.cmbCleanTarget.setCurrentIndex(0)
    assert settings_dialog.ui.chkCleanEnabled.isChecked() is True
    assert settings_dialog.ui.inpCleanDays.value() == 30

    qtbot.mouseClick(settings_dialog.ui.chkCleanEnabled, Qt.MouseButton.LeftButton)
    settings_dialog.ui.inpCleanDays.setValue(45)

    settings_dialog.ui.cmbCleanTarget.setCurrentIndex(1)
    assert settings_dialog.ui.chkCleanEnabled.isChecked() is False

    settings_dialog.ui.cmbCleanTarget.setCurrentIndex(0)
    assert settings_dialog.ui.chkCleanEnabled.isChecked() is False
    assert settings_dialog.ui.inpCleanDays.value() == 45


def test_save_settings(settings_dialog: SettingsDialog, qtbot) -> None:
    """Перевіряє фінальне збереження налаштувань."""
    from PyQt6.QtCore import Qt

    settings_dialog.ui.inpMaxRadius.setValue(250.0)
    settings_dialog.ui.inpGpsInterval.setValue(30)

    with qtbot.waitSignal(settings_dialog.finished, timeout=1000) as blocker:
        qtbot.mouseClick(settings_dialog.ui.btnSave, Qt.MouseButton.LeftButton)

    assert blocker.args == [QDialog.DialogCode.Accepted], (
        "Dialog did not return Accepted status"
    )

    new_data = settings_dialog.get_settings()
    assert isinstance(new_data, SettingsData)
    assert new_data.radar_max_radius_km == 250.0
    assert new_data.gps_interval_s == 30


def test_restart_app_logout(
    settings_dialog: SettingsDialog, mock_settings: MagicMock, qtbot
) -> None:
    """Перевіряє функціонал виходу з системи."""
    from PyQt6.QtCore import Qt

    with patch("app.widgets.settings_dialog.restart_process") as mock_restart:
        qtbot.mouseClick(settings_dialog.ui.btnLogout, Qt.MouseButton.LeftButton)

        assert mock_settings.remember_me is False, "'remember_me' flag was not reset"
        assert mock_restart.called, "Process restart function was not called"
