"""
Тести для компонентів рендерингу (Renderers).
"""

import pytest
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap

from app.models.detection_event import DetectionEvent
from app.models.radar_target import RadarTarget
from app.models.source_type import SourceType
from app.ui.components.radar_renderer import RadarRenderer


@pytest.fixture
def radar_renderer():
    return RadarRenderer()


def test_radar_renderer_draw_detections(qtbot, radar_renderer):
    """Тест малювання точок на радарі."""
    # Створюємо порожній Pixmap
    base = QPixmap(500, 500)
    base.fill(Qt.GlobalColor.black)

    event = DetectionEvent(
        id="t1",
        type=SourceType.RF,
        name="Drone",
        object_class="drone",
        confidence=0.9,
        timestamp="2026-05-30T12:00:00",
        distance_km=0.5,
        angle=45.0,
        frequency_hz=2.4e9,
    )
    target = RadarTarget(event=event, visual_index=1)

    # Викликаємо малювання (має повернути новий Pixmap)
    result = radar_renderer.draw_detections(base, [target], max_radius_km=1.0)

    assert isinstance(result, QPixmap)
    assert not result.isNull()
    assert result.size() == base.size()


def test_radar_renderer_get_target_at_position(qtbot, radar_renderer):
    """Тест визначення цілі за координатами кліку."""
    base = QPixmap(500, 500)
    event = DetectionEvent(
        id="t1",
        type=SourceType.RF,
        name="Drone",
        object_class="drone",
        confidence=0.9,
        timestamp="2026-05-30T12:00:00",
        distance_km=0.5,
        angle=90.0,
        frequency_hz=2.4e9,
    )
    # angle=90 на радарі (з врахуванням RADAR_ANGLE_ROTATION_OFFSET=90)
    # це точка справа по горизонталі (x = center + dist)
    target = RadarTarget(event=event, visual_index=42)

    radar_renderer.draw_detections(base, [target], max_radius_km=1.0)

    # Центр (250, 250), радіус 250 пікселів.
    # При dist=0.5км та max=1.0км, pixel_dist = 125.
    # angle=90-90 = 0 радіан (косинус=1, синус=0).
    # Очікувані координати: (250 + 125, 250 + 0) = (375, 250)

    found_id = radar_renderer.get_target_id_at_position(375, 250, tolerance_px=10)
    assert found_id == 42

    # Клік мимо
    assert radar_renderer.get_target_id_at_position(0, 0) is None


def test_radar_renderer_scan_animation(qtbot, radar_renderer):
    """Тест малювання анімації сканування."""
    size = QSize(500, 500)

    # Перший кадр
    p1 = radar_renderer.draw_scan_animation(size, has_detections=False)
    angle1 = radar_renderer.radar_angle

    # Другий кадр
    p2 = radar_renderer.draw_scan_animation(size, has_detections=True)
    angle2 = radar_renderer.radar_angle

    assert angle2 == (angle1 + 6) % 360
    assert not p1.isNull()
    assert not p2.isNull()
