import math


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Обчислює відстань між двома точками в метрах за формулою гаверсинусів."""
    r_earth = 6371000  # Радіус Землі в метрах
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r_earth * c
