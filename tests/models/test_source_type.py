"""Тести для перевірки переліку типів джерел сигналів SourceType."""

from app.models.source_type import SourceType


def test_source_type_values() -> None:
    assert SourceType.RF.value == "RF", "RF value should be 'RF'"
    assert SourceType.SOUND.value == "Sound", "SOUND value should be 'Sound'"


def test_source_type_count() -> None:
    assert len(SourceType) == 2, "SourceType count should be 2"
