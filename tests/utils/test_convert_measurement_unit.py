"""
Тести для функцій конвертації одиниць виміру (convert_measurement_unit).
"""

from app.utils.convert_measurement_unit import (
    convert_ghz_to_hz,
    convert_hz_to_ghz,
    convert_hz_to_mhz,
    convert_mhz_to_hz,
)


def test_conversions():
    """Тест усіх функцій конвертації одиниць виміру."""
    # GHz <-> Hz
    assert convert_ghz_to_hz(2.4) == 2_400_000_000
    assert convert_hz_to_ghz(2_400_000_000) == 2.4
    assert convert_hz_to_ghz(2_400_500_000) == 2.401  # Перевірка округлення до 3 знаків

    # MHz <-> Hz
    assert convert_mhz_to_hz(433.92) == 433_920_000
    assert convert_hz_to_mhz(433_920_000) == 433.9
    assert convert_hz_to_mhz(433_960_000) == 434.0  # Перевірка округлення до 1 знака
