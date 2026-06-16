import math
from typing import Dict, List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter

from app.core.chart_theme import ChartTheme
from app.core.constants import UINT8_MAX, VISUAL_NOISE_FLOOR_UINT8


class ChartMath:
    """Математичні обчислення та утиліти для побудови графіків спектра та водоспаду."""

    # Кеш для палітри кольорів водоспаду (ARGB LUT).
    _cached_color_table: Optional[List[int]] = None

    @staticmethod
    def calculate_nice_axis(
        max_val: float, target_ticks: int = 5
    ) -> Tuple[float, float, int]:
        """Розрахунок оптимальних кроків та меж для осей графіків."""
        if max_val <= 0:
            return 10.0, 1.0, 10

        # Розрахунок приблизного кроку та його порядку величини
        raw_step = max_val / target_ticks
        mag = math.floor(math.log10(raw_step))
        mag_pow = 10**mag
        mag_norm = raw_step / mag_pow

        # Вибір "красивого" множника (1, 2, 5 або 10)
        if mag_norm < 1.5:
            nice_step_norm = 1.0
        elif mag_norm < 3.0:
            nice_step_norm = 2.0
        elif mag_norm < 7.0:
            nice_step_norm = 5.0
        else:
            nice_step_norm = 10.0

        nice_step = nice_step_norm * mag_pow

        # Вирівнювання для уникнення дробових кроків при великих значеннях
        if max_val > 10 and nice_step < 1:
            nice_step = 1.0
        elif nice_step >= 1:
            nice_step = int(nice_step)

        nice_max = math.ceil(max_val / nice_step) * nice_step
        actual_ticks = int(nice_max / nice_step)

        return nice_max, nice_step, actual_ticks

    @classmethod
    def create_heatmap(cls, data: np.ndarray) -> QImage:
        """Створення QImage з масиву NumPy для візуалізації водоспаду."""
        h, w = data.shape
        # data.data.tobytes() забезпечує швидкий доступ до пам'яті масиву
        img = QImage(data.data.tobytes(), w, h, w, QImage.Format.Format_Indexed8)
        img.setColorTable(cls._get_color_table())
        return img.copy()

    @classmethod
    def _get_color_table(cls) -> List[int]:
        """Генерує та кешує таблицю кольорів для водоспаду."""
        if cls._cached_color_table:
            return cls._cached_color_table

        gradient = QLinearGradient(0, 0, UINT8_MAX, 0)
        stops = ChartTheme.WATERFALL_POS
        colors = ChartTheme.WATERFALL_COLORS

        # Розрахунок порогу шуму (0.0 - 1.0)
        noise_threshold_norm = min(VISUAL_NOISE_FLOOR_UINT8 / float(UINT8_MAX), 0.9)

        # Заповнення початкової частини градієнта кольором фону (шум)
        bg_color = QColor(*colors[0])
        gradient.setColorAt(0.0, bg_color)
        gradient.setColorAt(noise_threshold_norm, bg_color)

        remaining_space = 1.0 - noise_threshold_norm

        for theme_pos, color_tuple in zip(stops, colors):
            if theme_pos == 0.0:
                continue

            # Розподіл кольорів від порогу шуму до максимуму
            real_pos = min(noise_threshold_norm + (theme_pos * remaining_space), 1.0)
            gradient.setColorAt(real_pos, QColor(*color_tuple))

        # Рендеринг градієнта для отримання значень кольорів
        image = QImage(256, 1, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.fillRect(image.rect(), QBrush(gradient))
        painter.end()

        table = [image.pixel(i, 0) for i in range(256)]
        cls._cached_color_table = table
        return table

    @staticmethod
    def get_color_for_id(obj_id: str, cache: Dict[str, QColor]) -> QColor:
        """Генерує або дістає з кешу стабільний колір для ідентифікатора об'єкта."""
        if obj_id in cache:
            return cache[obj_id]

        idx = len(cache)
        # Золотий кут (137.508°) для оптимального розподілу відтінків
        hue = int((idx * 137.508) % 360)

        color = QColor.fromHsv(hue, 200, UINT8_MAX)
        cache[obj_id] = color
        return color
