import math


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Обчислює відстань між двома точками на сфері (Землі) за допомогою формули гаверсинусів.

    Args:
        lat1 (float): Широта першої точки в градусах.
        lon1 (float): Довгота першої точки в градусах.
        lat2 (float): Широта другої точки в градусах.
        lon2 (float): Довгота другої точки в градусах.

    Returns:
        float: Відстань між точками в метрах.

    Note:
        Використовується середній радіус Землі 6 371 000 метрів.
    """
    # Радіус Землі в метрах
    r_earth = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    # Обчислення квадрата половини хорди між точками
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    # Обчислення кутової відстані в радіанах
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r_earth * c
