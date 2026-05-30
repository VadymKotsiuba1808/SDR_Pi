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
    assert convert_ghz_to_hz(2.4) == 2_400_000_000, "GHz to Hz conversion error"
    assert convert_hz_to_ghz(2_400_000_000) == 2.4, "Hz to GHz conversion error"
    assert (
        convert_hz_to_ghz(2_400_500_000) == 2.401
    ), "Hz to GHz rounding error (expected 3 decimal places)"

    # MHz <-> Hz
    assert convert_mhz_to_hz(433.92) == 433_920_000, "MHz to Hz conversion error"
    assert convert_hz_to_mhz(433_920_000) == 433.9, "Hz to MHz conversion error"
    assert (
        convert_hz_to_mhz(433_960_000) == 434.0
    ), "Hz to MHz rounding error (expected 1 decimal place)"
