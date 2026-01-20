import math
import numpy as np
from typing import Tuple, Dict
from PyQt6.QtGui import QImage, QColor


class ChartMath:
    """Чиста математика та утиліти для графіків."""

    @staticmethod
    def calculate_nice_axis(
        max_val: float, target_ticks: int = 5
    ) -> Tuple[float, float, int]:
        """Розрахунок 'красивих' кроків для осей."""
        if max_val <= 0:
            return 10.0, 1.0, 10

        raw_step = max_val / target_ticks
        mag = math.floor(math.log10(raw_step))
        mag_pow = 10**mag
        mag_norm = raw_step / mag_pow

        if mag_norm < 1.5:
            nice_step_norm = 1.0
        elif mag_norm < 3.0:
            nice_step_norm = 2.0
        elif mag_norm < 7.0:
            nice_step_norm = 5.0
        else:
            nice_step_norm = 10.0

        nice_step = nice_step_norm * mag_pow

        if max_val > 10 and nice_step < 1:
            nice_step = 1.0
        elif nice_step >= 1:
            nice_step = int(nice_step)

        nice_max = math.ceil(max_val / nice_step) * nice_step
        actual_ticks = int(nice_max / nice_step)

        return nice_max, nice_step, actual_ticks

    @staticmethod
    def create_heatmap(data: np.ndarray) -> QImage:
        """Створення QImage з numpy масиву (для водоспаду)."""
        h, w = data.shape
        img = QImage(data.data, w, h, w, QImage.Format.Format_Indexed8)

        colors = []
        for i in range(256):
            t = i / 255.0
            r, g, b = 0, 0, 0

            if t < 0.35:
                b = int(t * 300)
            elif t < 0.5:
                b = max(0, int(100 - (t - 0.35) * 600))

            if t >= 0.35 and t < 0.6:
                r = int((t - 0.35) * 4 * 255)
            elif t >= 0.6:
                r = 255

            if t >= 0.6:
                g = int((t - 0.6) * 2.5 * 255)

            colors.append(QColor(r, g, b).rgb())

        img.setColorTable(colors)
        return img.copy()

    @staticmethod
    def get_color_for_id(obj_id: str, cache: Dict[str, QColor]) -> QColor:
        """Генерує або дістає з кешу стабільний колір для ID об'єкта."""
        if obj_id in cache:
            return cache[obj_id]

        idx = len(cache)
        hue = int((idx * 137.508) % 360)
        color = QColor.fromHsv(hue, 200, 255)
        cache[obj_id] = color
        return color
