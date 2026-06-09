"""
Тести для моделі RadarTarget.
"""

from datetime import datetime, timedelta

from app.models.detection_event import DetectionEvent
from app.models.radar_target import RadarTarget
from app.models.source_type import SourceType


def create_fake_event(dist=1.0, angle=45.0):
    return DetectionEvent(
        id="t1",
        type=SourceType.RF,
        name="Target",
        object_class="uav",
        confidence=0.8,
        timestamp=datetime.now().isoformat(),
        distance_km=dist,
        angle=angle,
        frequency_hz=2400,
    )


def test_radar_target_initialization():
    """Тест ініціалізації RadarTarget."""
    event = create_fake_event()
    target = RadarTarget(event=event, visual_index=1)

    assert target.id == "t1"
    assert target.visual_index == 1
    assert target.anchor_event == event


def test_radar_target_update_stationary():
    """Тест оновлення цілі без суттєвого руху."""
    event1 = create_fake_event(dist=1.0, angle=45.0)
    target = RadarTarget(event=event1, visual_index=1)

    # Невеликий рух (менше порогу 0.01 км)
    event2 = create_fake_event(dist=1.005, angle=45.5)
    target.update(event2)

    assert target.event == event2
    assert target.anchor_event == event1  # Якір не змінився


def test_radar_target_update_moved():
    """Тест оновлення цілі при суттєвому русі."""
    event1 = create_fake_event(dist=1.0, angle=45.0)
    target = RadarTarget(event=event1, visual_index=1)

    # Суттєвий рух (> 10 метрів)
    event2 = create_fake_event(dist=1.02, angle=45.0)
    target.update(event2)

    assert target.event == event2
    assert target.anchor_event == event2  # Якір оновився


def test_radar_target_expiration():
    """Тест перевірки застарілості цілі."""
    event = create_fake_event()
    target = RadarTarget(event=event, visual_index=1)

    # Імітуємо минулий час
    target.last_seen = datetime.now() - timedelta(seconds=10)

    assert target.is_expired(ttl_seconds=5) is True
    assert target.is_expired(ttl_seconds=15) is False


def test_radar_target_stationary_check():
    """Тест перевірки нерухомості."""
    event = create_fake_event()
    target = RadarTarget(event=event, visual_index=1)

    target.last_moved_time = datetime.now() - timedelta(seconds=10)

    assert target.is_stationary_for(seconds=5) is True
    assert target.is_stationary_for(seconds=15) is False
