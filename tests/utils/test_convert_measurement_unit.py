"""Тести конвертації одиниць виміру частоти."""

from app.utils.convert_measurement_unit import (
    convert_ghz_to_hz,
    convert_hz_to_ghz,
    convert_hz_to_mhz,
    convert_mhz_to_hz,
)


def test_conversions() -> None:
    assert convert_ghz_to_hz(2.4) == 2_400_000_000, "Error converting GHz to Hz"
    assert convert_hz_to_ghz(2_400_000_000) == 2.4, "Error converting Hz to GHz"
    assert convert_hz_to_ghz(2_400_500_000) == 2.401, (
        "Rounding error Hz to GHz (3 decimal places precision expected)"
    )

    assert convert_mhz_to_hz(433.92) == 433_920_000, "Error converting MHz to Hz"
    assert convert_hz_to_mhz(433_920_000) == 433.9, "Error converting Hz to MHz"
    assert convert_hz_to_mhz(433_960_000) == 434.0, (
        "Rounding error Hz to MHz (1 decimal place precision expected)"
    )
