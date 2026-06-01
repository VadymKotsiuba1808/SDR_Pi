import math

from PyQt6.QtCore import QPointF, QRect, QSize, Qt
from PyQt6.QtGui import QPixmap


class MapViewLogic:
    """
    Клас для обробки логіки відображення мапи:
    розрахунок масштабу та генерація обрізаного зображення (viewport).
    """

    @staticmethod
    def calculate_scale_factor(
        radar_radius_km: float, radar_view_width_px: int, map_resolution_km_px: float
    ) -> float:
        """
        Розраховує коефіцієнт масштабування між фізичною мапою та відображенням на екрані.

        Цей коефіцієнт використовується для приведення пікселів вхідної мапи до пікселів
        віджету відображення, враховуючи заданий радіус огляду радара.

        Args:
            radar_radius_km: Радіус огляду радара в кілометрах.
            radar_view_width_px: Ширина віджету радара в пікселях.
            map_resolution_km_px: Роздільна здатність мапи (кілометрів на піксель).

        Returns:
            float: Коефіцієнт масштабування. Повертає 0.0, якщо вхідні параметри некоректні.
        """
        if radar_radius_km <= 0:
            return 0.0

        radar_view_radius_px = radar_view_width_px / 2.0

        # Визначаємо скільки пікселів екрана припадає на 1 км реального простору
        target_px_per_km = radar_view_radius_px / radar_radius_km

        if map_resolution_km_px <= 0:
            return 0.0

        # Визначаємо скільки пікселів мапи-джерела припадає на 1 км
        source_px_per_km = 1.0 / map_resolution_km_px

        return target_px_per_km / source_px_per_km

    @staticmethod
    def generate_view_pixmap(
        source_map: QPixmap,
        view_size: QSize,
        radar_center_relative: QPointF,
        scale_factor: float,
    ) -> QPixmap:
        """
        Створює фрагмент мапи (viewport) для відображення у віджеті.

        Вирізає частину мапи та масштабує її так, щоб центр радара відповідав
        заданим відносним координатам.

        Args:
            source_map: Оригінальне зображення мапи.
            view_size: Розмір цільового вікна відображення.
            radar_center_relative: Координати центру радара відносно центру мапи (в пікселях мапи).
            scale_factor: Коефіцієнт масштабування, розрахований через `calculate_scale_factor`.

        Returns:
            QPixmap: Оброблений фрагмент мапи або порожній QPixmap у разі помилки.
        """
        view_w = view_size.width()
        view_h = view_size.height()

        if view_w <= 0 or view_h <= 0 or source_map.isNull() or scale_factor <= 0.0001:
            return QPixmap()

        orig_w = source_map.width()
        orig_h = source_map.height()
        # Початкова точка відліку (центр мапи)
        gps_cx = orig_w / 2.0
        gps_cy = orig_h / 2.0

        rx = radar_center_relative.x()
        ry = radar_center_relative.y()

        # Обчислюємо верхній лівий кут області вирізання
        crop_x = gps_cx - (rx / scale_factor)
        crop_y = gps_cy - (ry / scale_factor)

        crop_w = view_w / scale_factor
        crop_h = view_h / scale_factor

        # Використовуємо ceil, щоб гарантувати, що вирізана область
        # повністю покриває необхідний viewport без щілин
        rect_x = int(crop_x)
        rect_y = int(crop_y)
        rect_w = int(math.ceil(crop_w))
        rect_h = int(math.ceil(crop_h))

        cropped = source_map.copy(rect_x, rect_y, rect_w, rect_h)

        if cropped.isNull():
            return QPixmap()

        return cropped.scaled(
            view_w,
            view_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    @staticmethod
    def calculate_map_expansion_coefficients(
        radar_rect: QRect, background_width: int, background_height: int
    ) -> list[float]:
        """
        Розраховує коефіцієнти розширення мапи для повного заповнення фону.

        Визначає, наскільки потрібно збільшити область мапи, щоб при будь-якому положенні
        центра радара мапа повністю покривала прямокутник фону.

        Args:
            radar_rect: Прямокутник, що описує область радара.
            background_width: Повна ширина фонового віджету.
            background_height: Повна висота фонового віджету.

        Returns:
            list[float]: Список з двох значень [k_w, k_h] — коефіцієнти розширення.
        """
        if not radar_rect.width() or not radar_rect.height():
            return [1.0, 1.0]

        rx = radar_rect.center().x()
        ry = radar_rect.center().y()

        # Знаходимо максимальну відстань від центра радара до країв фону
        max_dist_x = max(rx, background_width - rx)
        max_dist_y = max(ry, background_height - ry)

        radar_radius_px = radar_rect.width() / 2.0
        if radar_radius_px <= 0:
            return [1.0, 1.0]

        k_w = max_dist_x / radar_radius_px
        k_h = max_dist_y / radar_radius_px

        # Додаємо 5% запас (1.05), щоб уникнути артефактів на краях мапи при рендерингу
        return [k_w * 1.05, k_h * 1.05]
