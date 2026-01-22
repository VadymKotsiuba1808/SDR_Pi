from typing import Final, Tuple
from PyQt6.QtGui import QColor


class ChartTheme:
    """Централізоване сховище кольорів."""

    # --- Для StaticChartWidget (QColor) ---
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

    # --- Для DynamicChartWidget ---
    DYN_BACKGROUND: Final[str] = "#1a1a1a"
    DYN_FOREGROUND: Final[str] = "#d0d0d0"
    DYN_SPECTRUM_PEN: Final[str] = "#FFD700"
    DYN_CROSSHAIR_PEN: Final[str] = "#00FF00"

    # Waterfall Colormap (pos, color)
    WATERFALL_POS: Final[tuple] = (0.0, 0.2, 0.35, 0.6, 0.85)

    WATERFALL_COLORS: Final[tuple] = (
        (0, 0, 30, 255),  # 0.00: Темно-синій (фон)
        (0, 50, 200, 255),  # 0.20: Насичений синій (слабкий сигнал)
        (180, 60, 0, 255),  # 0.35: ОРАНЖЕВИЙ (початок сильного сигналу)
        (255, 0, 0, 255),  # 0.60: Червоний (дуже сильний сигнал)
        (255, 255, 0, 255),  # 0.85: Жовтий (пік/максимум)
    )
