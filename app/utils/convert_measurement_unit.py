def convert_ghz_to_hz(value: float) -> int:
    return int(float(value) * 1_000_000_000)


def convert_hz_to_ghz(value: float) -> float:
    return round(float(float(value) / 1_000_000_000), 3)


def convert_mhz_to_hz(value: float) -> int:
    return int(float(value) * 1_000_000)


def convert_hz_to_mhz(value: float) -> float:
    return round(float(float(value) / 1_000_000), 1)
