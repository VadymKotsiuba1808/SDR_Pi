"""
Тести для моделі SourceType.
"""

from app.models.source_type import SourceType


def test_source_type_values():
    """Перевірка значень переліку SourceType."""
    assert SourceType.RF.value == "RF"
    assert SourceType.SOUND.value == "Sound"


def test_source_type_count():
    """Перевірка кількості типів джерел."""
    assert len(SourceType) == 2
