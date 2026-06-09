"""
Тести для утиліти наповнення БД (populate_db_util).
"""

from unittest.mock import MagicMock, patch

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from pi_server.populate_db_util import run_seeding


def test_run_seeding_calls_db_methods():
    """
    Тест виконання run_seeding.
    Перевіряємо, що методи add_class та add_object викликаються потрібну кількість разів.
    """
    mock_db_instance = MagicMock()

    # Мокаємо QCoreApplication, QEventLoop та QTimer, щоб тест не зависав на очікуванні
    with (
        patch(
            "pi_server.populate_db_util.DatabaseService", return_value=mock_db_instance
        ),
        patch("pi_server.populate_db_util.QCoreApplication"),
        patch("pi_server.populate_db_util.QEventLoop.exec"),
        patch("pi_server.populate_db_util.time.sleep"),
    ):  # Прискорюємо тест
        run_seeding()

        # Перевіряємо кількість доданих класів (6 за списком у файлі)
        assert mock_db_instance.add_class.call_count == 6, (
            "Should call add_class 6 times"
        )

        # Перевіряємо, що перший клас - Recon Drone
        first_class_call = mock_db_instance.add_class.call_args_list[0][0][0]
        assert isinstance(first_class_call, ObjectClass)
        assert first_class_call.name == "Recon Drone"

        # Перевіряємо кількість доданих сигнатур (12 за списком у файлі)
        assert mock_db_instance.add_object.call_count == 12, (
            "Should call add_object 12 times"
        )

        # Перевіряємо одну з сигнатур (наприклад, Shahed-136)
        # Вона йде 3-ю та 4-ю у списку
        third_obj_call = mock_db_instance.add_object.call_args_list[2][0][0]
        assert isinstance(third_obj_call, DetectionObject)
        assert third_obj_call.name == "Shahed-136"
        assert third_obj_call.class_id == 2
