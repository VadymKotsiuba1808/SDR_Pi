from typing import Final

from PyQt6.QtGui import QColor


class ChartTheme:
    """
    Централізоване сховище кольорів та стилів для компонентів графіків.

    Клас містить статичні константи, які визначають візуальний вигляд спектрограм,
    осцилограм та водоспадів у застосунку.

    Attributes:
        BG (QColor): Колір фону для статичного графіка (напівпрозорий темно-зелений).
        GRID (QColor): Основний колір сітки.
        GRID_FAINT (QColor): Колір допоміжної (тьмяної) сітки.
        TEXT (QColor): Основний колір тексту міток та осей.
        HIGHLIGHT (QColor): Колір для виділення важливих елементів (наприклад, курсору).
        HIGHLIGHT_BG (QColor): Колір фону для підказок або виділених областей.
        SPECTRUM_MAX (QColor): Колір лінії максимальних значень спектру.
        SPECTRUM_AVG_FILL (QColor): Початковий колір градієнта заливки середнього спектру.
        SPECTRUM_AVG_END (QColor): Кінцевий колір градієнта заливки середнього спектру.
        SPECTRUM_MAX_GLOW (QColor): Колір ефекту "світіння" для пікових значень.
        DYN_BACKGROUND (str): Колір фону для динамічного графіка (HEX).
        DYN_FOREGROUND (str): Колір переднього плану (осей, тексту) для динамічного графіка.
        DYN_SPECTRUM_PEN (str): Колір пера для малювання лінії спектру.
        DYN_CROSSHAIR_PEN (str): Колір пера для перехрестя (курсору).
        WATERFALL_POS (tuple[float, ...]): Позиції контрольних точок для колірної карти водоспаду.
        WATERFALL_COLORS (tuple[tuple[int, int, int, int], ...]): Кольори (RGBA) для водоспаду.
    """

    # --- Константи для StaticChartWidget (QColor) ---
    # Використовуються для малювання через QPainter у статичних віджетах.

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

    # --- Константи для DynamicChartWidget (рядок HEX) ---
    # Використовуються переважно в pyqtgraph, де зручніше передавати рядки або HEX.

    DYN_BACKGROUND: Final[str] = "#1a1a1a"
    DYN_FOREGROUND: Final[str] = "#d0d0d0"
    DYN_SPECTRUM_PEN: Final[str] = "#FFD700"
    DYN_CROSSHAIR_PEN: Final[str] = "#00FF00"

    # --- Налаштування колірної карти Waterfall ---

    # Позиції від 0.0 до 1.0, що визначають розподіл кольорів.
    WATERFALL_POS: Final[tuple[float, ...]] = (0.0, 0.2, 0.35, 0.6, 0.85)

    # Список кольорів (R, G, B, A), що відповідають позиціям WATERFALL_POS.
    # Колірна схема переходить від глибокого синього (шум) до яскраво-жовтого (пік).
    WATERFALL_COLORS: Final[tuple[tuple[int, int, int, int], ...]] = (
        (0, 0, 30, 255),  # 0.00: Темно-синій (фон)
        (0, 50, 200, 255),  # 0.20: Насичений синій (слабкий сигнал)
        (180, 60, 0, 255),  # 0.35: Оранжевий (початок сильного сигналу)
        (255, 0, 0, 255),  # 0.60: Червоний (дуже сильний сигнал)
        (255, 255, 0, 255),  # 0.85: Жовтий (пік/максимум)
    )
