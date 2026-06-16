"""Тести для моделі CleanRule."""

from app.models.settings import CleanRule


def test_clean_rule_serialization() -> None:
    rule = CleanRule(enabled=True, days=15)
    data = rule.to_dict()

    assert data["enabled"] is True, "The 'enabled' field should be True"
    assert data["days"] == 15, "The 'days' field should be 15"


def test_clean_rule_from_dict() -> None:
    data = {"enabled": True, "days": 10}
    rule = CleanRule.from_dict(data)

    assert rule.enabled is True, "The 'enabled' attribute should be True"
    assert rule.days == 10, "The 'days' attribute should be 10"


def test_clean_rule_from_dict_empty() -> None:
    rule = CleanRule.from_dict({})
    assert rule.enabled is False, "By default 'enabled' should be False"
    assert rule.days == 30, "By default 'days' should be 30"
