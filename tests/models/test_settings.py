"""
Тести для моделі CleanRule (settings.py).
"""

from app.models.settings import CleanRule


def test_clean_rule_serialization():
    """Тест серіалізації CleanRule."""
    rule = CleanRule(enabled=True, days=15)
    data = rule.to_dict()

    assert data["enabled"] is True
    assert data["days"] == 15


def test_clean_rule_from_dict():
    """Тест десеріалізації CleanRule."""
    data = {"enabled": True, "days": 10}
    rule = CleanRule.from_dict(data)

    assert rule.enabled is True
    assert rule.days == 10


def test_clean_rule_from_dict_empty():
    """Тест десеріалізації порожнього CleanRule."""
    rule = CleanRule.from_dict({})
    assert rule.enabled is False
    assert rule.days == 30  # Дефолтне значення
