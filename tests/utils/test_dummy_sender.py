"""
Тести для симулятора (dummy_sender).
Перевірка логіки фізичної симуляції цілей.
"""

import math

from app.models.detection_object import DetectionObject
from app.utils.dummy_sender import SimulatedTarget


def test_simulated_target_initialization():
    """Тест ініціалізації симуляційної цілі."""
    template = DetectionObject(
        id=None,
        name="Mavic 3",
        class_id=1,
        object_class="UAV",
        is_dangerous=True,
        rf_params_hz=["2400000000-2483500000"],
        sound_params_hz=[],
    )

    target = SimulatedTarget(template)

    assert target.name == "Mavic 3"
    assert target.is_dangerous is True
    assert 2.4e9 <= target.base_freq <= 2.4835e9
    assert math.sqrt(target.x**2 + target.y**2) > 0


def test_simulated_target_movement():
    """Тест руху цілі."""
    template = DetectionObject(id=None, name="Test", class_id=1, object_class="X")
    target = SimulatedTarget(template)

    initial_x, initial_y = target.x, target.y

    # Оновлюємо фізику (dt = 1.0 сек)
    target.update(1.0)

    assert (target.x != initial_x) or (target.y != initial_y), "Target should move"


def test_simulated_target_event_generation():
    """Тест генерації даних події."""
    template = DetectionObject(id=None, name="Test", class_id=1, object_class="X")
    target = SimulatedTarget(template)

    event = target.get_event_data()

    assert event is not None
    assert "distance_km" in event
    assert "angle" in event
    assert event["name"] == "Test"


def test_simulated_target_background_generation():
    """Тест генерації фонових спектральних даних."""
    template = DetectionObject(id=None, name="Test", class_id=1, object_class="X")
    target = SimulatedTarget(template)

    bg = target.check_and_get_background()

    assert bg is not None
    assert "spectral_data" in bg
    assert len(bg["spectral_data"]["data_magnitude"]) > 0
