"""Тести для компонентів рендерингу радару."""

import pytest
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap

from app.models.detection_event import DetectionEvent
from app.models.radar_target import RadarTarget
from app.models.source_type import SourceType
from app.ui.components.radar_renderer import RadarRenderer


@pytest.fixture
def radar_renderer() -> RadarRenderer:
    return RadarRenderer()


def test_radar_renderer_draw_detections(qtbot, radar_renderer: RadarRenderer) -> None:
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

    result = radar_renderer.draw_detections(base, [target], max_radius_km=1.0)

    assert isinstance(result, QPixmap), "An object of type QPixmap should be returned"
    assert not result.isNull(), "Result should not be empty"
    assert result.size() == base.size(), "Size should match the base Pixmap"


def test_radar_renderer_get_target_at_position(
    qtbot, radar_renderer: RadarRenderer
) -> None:
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
    target = RadarTarget(event=event, visual_index=42)

    radar_renderer.draw_detections(base, [target], max_radius_km=1.0)

    # Розрахунок: центр (250, 250), r=250. Відстань 125px при куті 90 (x=375, y=250)
    found_id = radar_renderer.get_target_id_at_position(375, 250, tolerance_px=10)
    assert found_id == 42, "Target with visual_index=42 should be found"

    assert radar_renderer.get_target_id_at_position(0, 0) is None, (
        "No targets should be found outside the object"
    )


def test_radar_renderer_scan_animation(qtbot, radar_renderer: RadarRenderer) -> None:
    size = QSize(500, 500)

    p1 = radar_renderer.draw_scan_animation(size, has_detections=False)
    angle1 = radar_renderer.radar_angle

    p2 = radar_renderer.draw_scan_animation(size, has_detections=True)
    angle2 = radar_renderer.radar_angle

    assert angle2 == (angle1 + 6) % 360, "Angle should shift by 6 degrees"
    assert not p1.isNull(), "First animation frame should be valid"
    assert not p2.isNull(), "Second animation frame should be valid"
