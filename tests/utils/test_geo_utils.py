"""
Тести для географічних утиліт.
"""

from app.utils.geo_utils import calculate_distance


def test_calculate_distance_same_point():
    """Перевірка відстані між однією і тією ж точкою (має бути 0)."""
    lat, lon = 50.45, 30.52
    assert calculate_distance(lat, lon, lat, lon) == 0


def test_calculate_distance_known_points():
    """
    Перевірка відстані між відомими точками (Київ та Львів).
    Приблизна відстань ~468 км.
    """
    kyiv = (50.45, 30.52)
    lviv = (49.84, 24.03)

    dist = calculate_distance(kyiv[0], kyiv[1], lviv[0], lviv[1])

    # Допустима похибка 1% через особливості розрахунків на сфері vs еліпсоїді
    assert 460000 < dist < 480000


def test_calculate_distance_small_offset():
    """Перевірка на малих відстанях."""
    lat1, lon1 = 50.0, 30.0
    lat2, lon2 = 50.0001, 30.0001  # ~14 метрів

    dist = calculate_distance(lat1, lon1, lat2, lon2)
    assert 10 < dist < 20
