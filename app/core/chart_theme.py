from typing import Final

from PyQt6.QtGui import QColor


class ChartTheme:
    """Централізоване сховище кольорів та стилів для компонентів графіків.

    Клас містить статичні константи, які визначають візуальний вигляд спектрограм,
    осцилограм та водоспадів у застосунку.

    Attributes:
        BG, GRID, GRID_FAINT: Кольори фону та сітки для статичних графіків.
        TEXT, HIGHLIGHT, HIGHLIGHT_BG: Кольори тексту та виділення.
        SPECTRUM_*: Стилі ліній та заливки спектру.
        DYN_*: Налаштування для динамічних графіків (pyqtgraph).
        WATERFALL_*: Параметри колірної карти водоспаду.
    """

    BG: Final[QColor] = QColor(0, 20, 0, 100)
    GRID: Final[QColor] = QColor(50, 136, 68, 100)
    GRID_FAINT: Final[QColor] = QColor(100, 150, 100, 50)
    TEXT: Final[QColor] = QColor(200, 200, 200)
    HIGHLIGHT: Final[QColor] = QColor(255, 255, 0)
    HIGHLIGHT_BG: Final[QColor] = QColor(0, 0, 0, 220)
    SPECTRUM_MAX: Final[QColor] = QColor("#FFD700")
    SPECTRUM_AVG_FILL: Final[QColor] = QColor(0, 255, 255, 100)
    SPECTRUM_AVG_END: Final[QColor] = QColor(0, 255, 255, 10)
    SPECTRUM_MAX_GLOW: Final[QColor] = QColor(255, 215, 0, 50)

    DYN_BACKGROUND: Final[str] = "#1a1a1a"
    DYN_FOREGROUND: Final[str] = "#d0d0d0"
    DYN_SPECTRUM_PEN: Final[str] = "#FFD700"
    DYN_CROSSHAIR_PEN: Final[str] = "#00FF00"

    WATERFALL_POS: Final[tuple[float, ...]] = (0.0, 0.2, 0.35, 0.6, 0.85)
    WATERFALL_COLORS: Final[tuple[tuple[int, int, int, int], ...]] = (
        (0, 0, 30, 255),  # Темно-синій (фон)
        (0, 50, 200, 255),  # Насичений синій
        (180, 60, 0, 255),  # Оранжевий
        (255, 0, 0, 255),  # Червоний
        (255, 255, 0, 255),  # Жовтий (пік)
    )
