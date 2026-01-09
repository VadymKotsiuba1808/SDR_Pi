def convert_ghz_to_hz(value: float) -> int:
    return int(value * 1_000_000_000)


def convert_hz_to_ghz(value: float) -> float:
    return float(value / 1_000_000_000)
