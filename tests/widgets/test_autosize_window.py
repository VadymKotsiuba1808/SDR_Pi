"""
Тести для модуля автоматичного масштабування (Autosize Window).
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QComboBox, QMainWindow, QWidget

from app.widgets.autosize_window import ScaledComboBox, enable_auto_scaling


def test_enable_auto_scaling_smoke(qtbot):
    """
    Базовий тест (smoke test) для перевірки того, що функція масштабування
    не викликає критичних помилок на стандартному вікні.
    """
    window = QMainWindow()
    central = QWidget()
    window.setCentralWidget(central)

    # Додаємо комбобокс для перевірки заміни
    combo = QComboBox(central)
    combo.setObjectName("testCombo")
    combo.addItem("Item 1")

    # Мокаємо первинний екран для стабільності на різних системах
    with patch("PyQt6.QtGui.QGuiApplication.primaryScreen") as mock_screen:
        mock_rect = MagicMock()
        mock_rect.width.return_value = 1920
        mock_rect.height.return_value = 1080
        mock_screen.return_value.geometry.return_value = mock_rect

        enable_auto_scaling(window)

    # Перевіряємо, що старий віджет сховано
    assert combo.isVisible() is False

    # Перевіряємо, що в сцені з'явився новий віджет (ScaledComboBox)
    # Оскільки функція змінює centralWidget вікна на QGraphicsView
    from PyQt6.QtWidgets import QGraphicsView

    assert isinstance(window.centralWidget(), QGraphicsView)


def test_scaled_combo_box_init():
    """Тест ініціалізації ScaledComboBox."""
    old_combo = QComboBox()
    style = {"background": "red", "color": "white", "border": "none"}

    scaled = ScaledComboBox(style_data=style, old_combo_to_forward_to=old_combo)
    assert scaled.hidden_combo == old_combo
    assert scaled._menu_style_data["background"] == "red"
