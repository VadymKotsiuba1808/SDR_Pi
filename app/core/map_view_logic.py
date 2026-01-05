import math
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize, QPointF, QRect


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
        Розраховує коефіцієнт масштабування (scale_factor) між реальною мапою та відображенням на екрані.

        """
        if radar_radius_km <= 0:
            return 0.0

        radar_view_radius_px = radar_view_width_px / 2.0

        target_px_per_km = radar_view_radius_px / radar_radius_km

        if map_resolution_km_px <= 0:
            return 0.0

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
        Вирізає та масштабує частину мапи, щоб центр радара збігався з GPS-координатами.

        """
        view_w = view_size.width()
        view_h = view_size.height()

        if view_w <= 0 or view_h <= 0 or source_map.isNull() or scale_factor <= 0.0001:
            return QPixmap()

        orig_w = source_map.width()
        orig_h = source_map.height()
        gps_cx = orig_w / 2.0
        gps_cy = orig_h / 2.0

        rx = radar_center_relative.x()
        ry = radar_center_relative.y()

        crop_x = gps_cx - (rx / scale_factor)
        crop_y = gps_cy - (ry / scale_factor)

        crop_w = view_w / scale_factor
        crop_h = view_h / scale_factor

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
        Розраховує, наскільки треба розширити мапу, щоб вона займала фон повністю
        """
        if not radar_rect.width() or not radar_rect.height():
            return [1.0, 1.0]

        rx = radar_rect.center().x()
        ry = radar_rect.center().y()

        max_dist_x = max(rx, background_width - rx)
        max_dist_y = max(ry, background_height - ry)

        radar_radius_px = radar_rect.width() / 2.0
        if radar_radius_px <= 0:
            return [1.0, 1.0]

        k_w = max_dist_x / radar_radius_px
        k_h = max_dist_y / radar_radius_px

        return [k_w * 1.05, k_h * 1.05]
