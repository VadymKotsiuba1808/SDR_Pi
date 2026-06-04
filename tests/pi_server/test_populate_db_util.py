"""Тести для утиліти наповнення бази даних."""

from unittest.mock import MagicMock, patch

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from pi_server.populate_db_util import run_seeding


def test_run_seeding_calls_db_methods() -> None:
    """Тестує процес наповнення БД (seeding)."""
    mock_db_instance = MagicMock()

    # Мокаємо Qt та системні затримки для ізольованого тестування
    with (
        patch(
            "pi_server.populate_db_util.DatabaseService", return_value=mock_db_instance
        ),
        patch("pi_server.populate_db_util.QCoreApplication"),
        patch("pi_server.populate_db_util.QEventLoop.exec"),
        patch("pi_server.populate_db_util.time.sleep"),
    ):
        run_seeding()

        assert mock_db_instance.add_class.call_count == 6, (
            "add_class should be called 6 times"
        )

        first_class_call = mock_db_instance.add_class.call_args_list[0][0][0]
        assert isinstance(first_class_call, ObjectClass)
        assert first_class_call.name == "Recon Drone"

        assert mock_db_instance.add_object.call_count == 12, (
            "add_object should be called 12 times"
        )

        third_obj_call = mock_db_instance.add_object.call_args_list[2][0][0]
        assert isinstance(third_obj_call, DetectionObject)
        assert third_obj_call.name == "Shahed-136"
        assert third_obj_call.class_id == 2
