"""Модуль для тестування симулятора цілей (dummy_sender)."""

import math

from app.models.detection_object import DetectionObject
from app.utils.dummy_sender import SimulatedTarget


def test_simulated_target_initialization() -> None:
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

    assert target.name == "Mavic 3", "Target name should match the template"
    assert target.is_dangerous is True, "Danger status should match the template"
    assert 2.4e9 <= target.base_freq <= 2.4835e9, (
        "Base frequency should be within the specified range"
    )
    assert math.sqrt(target.x**2 + target.y**2) > 0, (
        "Initial coordinates should be non-zero"
    )


def test_simulated_target_movement() -> None:
    template = DetectionObject(id=None, name="Test", class_id=1, object_class="X")
    target = SimulatedTarget(template)

    initial_x, initial_y = target.x, target.y

    target.update(1.0)

    assert (target.x != initial_x) or (target.y != initial_y), (
        "Target should change position after update"
    )


def test_simulated_target_event_generation() -> None:
    template = DetectionObject(id=None, name="Test", class_id=1, object_class="X")
    target = SimulatedTarget(template)

    event = target.get_event_data()

    assert event is not None, "Event data should not be None"
    assert "distance_km" in event, "Event should contain distance"
    assert "angle" in event, "Event should contain angle"
    assert event["name"] == "Test", "Event name should match the template"


def test_simulated_target_background_generation() -> None:
    template = DetectionObject(id=None, name="Test", class_id=1, object_class="X")
    target = SimulatedTarget(template)

    bg = target.check_and_get_background()

    assert bg is not None, "Background data should not be None"
    assert "spectral_data" in bg, "Data should contain spectral information"
    assert len(bg["spectral_data"]["data_magnitude"]) > 0, (
        "Magnitude array should not be empty"
    )
