"""
Тести для віджета статичних графіків (StaticChartWidget).
"""

from unittest.mock import MagicMock

import pytest

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType
from app.widgets.static_chart_widget import StaticChartWidget


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.lang_code = "uk"
    return settings


@pytest.fixture
def static_chart(qtbot, mock_settings):
    """Фікстура для ініціалізації StaticChartWidget."""
    widget = StaticChartWidget(mock_settings)
    qtbot.addWidget(widget)
    return widget


def create_mock_events():
    return [
        DetectionEvent(
            id="1",
            type=SourceType.RF,
            name="Target 1",
            object_class="drone",
            confidence=0.9,
            timestamp="2026-05-30T12:00:00",
            distance_km=1.0,
            angle=45.0,
            frequency_hz=2.4e9,
        ),
        DetectionEvent(
            id="2",
            type=SourceType.RF,
            name="Target 2",
            object_class="bird",
            confidence=0.5,
            timestamp="2026-05-30T12:05:00",
            distance_km=2.5,
            angle=180.0,
            frequency_hz=433e6,
        ),
    ]


def test_initial_state(static_chart):
    """Тест початкового стану віджета."""
    assert static_chart.chart_type == "timeline"
    assert len(static_chart.data) == 0


def test_set_data(static_chart):
    """Тест встановлення даних для відображення."""
    events = create_mock_events()
    static_chart.set_data(events, highlight_ids={"1"})

    assert len(static_chart.data) == 2
    assert "1" in static_chart.highlight_ids
    # Дані мають бути відсортовані за часом
    assert static_chart.data[0].id == "1"


def test_set_chart_type(static_chart):
    """Тест зміни типу графіка."""
    static_chart.set_chart_type("spectrum")
    assert static_chart.chart_type == "spectrum"

    static_chart.set_chart_type("bar")
    assert static_chart.chart_type == "bar"


def test_get_active_event(static_chart):
    """Тест визначення активної події (для маркера)."""
    events = create_mock_events()
    static_chart.set_data(events)

    # Якщо нічого не підсвічено, активна - остання
    assert static_chart._get_active_event().id == "2"

    # Якщо підсвічено - активна підсвічена
    static_chart.set_data(events, highlight_ids={"1"})
    assert static_chart._get_active_event().id == "1"


def test_paint_event_no_data(static_chart, qtbot):
    """Тест відсутності крашів при малюванні без даних."""
    static_chart.update()
    # Просто перевіряємо, що метод викликається без винятків
    qtbot.waitExposed(static_chart)
