"""Юніт-тести для перевірки утиліт UI."""

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QWidget

from app.utils.ui_utils import move_dialog_down, update_element_styles


def test_update_element_styles(qtbot):
    """Перевіряє, що функція оновлення стилів викликається без винятків."""
    widget = QWidget()
    qtbot.addWidget(widget)

    # Перевіряємо стабільність механізму unpolish/polish PyQt на віджеті
    update_element_styles(widget)


def test_move_dialog_down(qtbot):
    """Перевіряє коректність позиціонування діалогового вікна відносно батьківської області."""
    dialog = QWidget()
    dialog.setFixedSize(100, 50)
    qtbot.addWidget(dialog)

    parent_geo = QRect(0, 0, 500, 500)
    move_dialog_down(dialog, parent_geo, offset_y=100)

    # Очікувані координати: центрування по X та заданий відступ по Y
    expected_x = 200  # (500 - 100) // 2
    expected_y = 100

    assert dialog.x() == expected_x, f"Expected x={expected_x}, got {dialog.x()}"
    assert dialog.y() == expected_y, f"Expected y={expected_y}, got {dialog.y()}"
