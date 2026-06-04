"""Тести для діалогу налаштування мапи."""

from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QCoreApplication, QPointF, Qt
from PyQt6.QtGui import QPixmap
from pytestqt.qtbot import QtBot

from app.widgets.set_map_dialog import SetMapDialog


@pytest.fixture
def mock_settings() -> MagicMock:
    """Створює макет налаштувань."""
    settings = MagicMock()
    settings.lang_code = "uk"
    settings.radar_max_radius_km = 1.0
    return settings


@pytest.fixture
def set_map_dialog(
    qtbot: QtBot, mock_settings: MagicMock
) -> Generator[SetMapDialog, None, None]:
    """Ініціалізує SetMapDialog."""
    dialog = SetMapDialog(mock_settings)
    qtbot.addWidget(dialog)
    yield dialog

    # Очищуємо транслятор після тесту
    QCoreApplication.removeTranslator(dialog.translator)


def test_initial_state(set_map_dialog: SetMapDialog) -> None:
    """Перевіряє початковий стан діалогу."""
    assert set_map_dialog.original_pixmap is None
    assert set_map_dialog.image_path == ""
    assert set_map_dialog.ui.scaleSpinBox.value() == 100
    assert set_map_dialog.ui.rotateSpinBox.value() == 0


def test_handle_select_image_success(
    set_map_dialog: SetMapDialog, tmp_path: Path
) -> None:
    """Перевіряє завантаження зображення мапи."""
    # Створюємо тимчасове червоне зображення
    img_path = str(tmp_path / "test_map.png")
    pixmap = QPixmap(100, 100)
    pixmap.fill(Qt.GlobalColor.red)
    pixmap.save(img_path)

    with patch(
        "PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=(img_path, "")
    ):
        set_map_dialog.handle_select_image()

    assert set_map_dialog.image_path == img_path
    assert set_map_dialog.original_pixmap is not None
    assert not set_map_dialog.original_pixmap.isNull()
    assert set_map_dialog.original_pixmap.width() == 100
    assert set_map_dialog.center_point_f == QPointF(49, 49)


def test_zoom_in_out(set_map_dialog: SetMapDialog, qtbot: QtBot) -> None:
    """Перевіряє роботу кнопок масштабування."""
    initial_scale = set_map_dialog.ui.scaleSpinBox.value()

    qtbot.mouseClick(set_map_dialog.ui.zoomInButton, Qt.MouseButton.LeftButton)
    assert set_map_dialog.ui.scaleSpinBox.value() == initial_scale + 1

    qtbot.mouseClick(set_map_dialog.ui.zoomOutButton, Qt.MouseButton.LeftButton)
    assert set_map_dialog.ui.scaleSpinBox.value() == initial_scale


def test_rotation_sync(set_map_dialog: SetMapDialog) -> None:
    """Перевіряє синхронізацію обертання."""
    # Зміна через спінбокс
    set_map_dialog.ui.rotateSpinBox.setValue(45)
    assert set_map_dialog.ui.rotateHorizontalSlider.value() == 45
    assert set_map_dialog.current_rotation == 45.0

    # Зміна через слайдер
    set_map_dialog.ui.rotateHorizontalSlider.setValue(90)
    assert set_map_dialog.ui.rotateSpinBox.value() == 90
    assert set_map_dialog.current_rotation == 90.0


def test_set_center_mode(
    set_map_dialog: SetMapDialog, qtbot: QtBot, tmp_path: Path
) -> None:
    """Перевіряє активацію режиму встановлення центру."""
    # Попередньо завантажуємо зображення
    img_path = str(tmp_path / "test_map.png")
    QPixmap(100, 100).save(img_path)
    with patch(
        "PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=(img_path, "")
    ):
        set_map_dialog.handle_select_image()

    qtbot.mouseClick(set_map_dialog.ui.setCenterButton, Qt.MouseButton.LeftButton)
    assert set_map_dialog.is_centering_mode is True
    assert (
        set_map_dialog.ui.mapDisplayLabel.cursor().shape() == Qt.CursorShape.CrossCursor
    )


def test_save_settings_success(
    set_map_dialog: SetMapDialog, tmp_path: Path, qtbot: QtBot
) -> None:
    """Перевіряє збереження налаштувань."""
    # 1. Завантаження тестового зображення
    img_path = str(tmp_path / "test_map.png")
    QPixmap(500, 500).save(img_path)
    with patch(
        "PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=(img_path, "")
    ):
        set_map_dialog.handle_select_image()

    # 2. Встановлення радіусу
    set_map_dialog.ui.radiusKmDoubleSpinBox.setValue(0.5)

    with qtbot.waitSignal(set_map_dialog.finished, timeout=1000) as blocker:
        qtbot.mouseClick(set_map_dialog.ui.saveButton, Qt.MouseButton.LeftButton)

    assert blocker.args == [1]
    settings = set_map_dialog.get_settings()
    assert settings is not None
    assert settings.rotation == 0
    assert isinstance(settings.pixmap, QPixmap)
