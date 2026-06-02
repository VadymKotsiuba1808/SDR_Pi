import sys
import time

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer

from app.core.logging_config import get_logger
from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from pi_server.database_service import DatabaseService

logger = get_logger(__name__)


def run_seeding() -> None:
    app = QCoreApplication(sys.argv)

    if not app:
        logger.error("Не вдалося створити екземпляр QCoreApplication.")
        return

    db = DatabaseService()
    loop = QEventLoop()

    classes_to_add = [
        "Recon Drone",
        "Loitering Munition",
        "FPV / Kamikaze",
        "Fixed Wing Recon",
        "False Alarm",
        "Interference",
    ]

    # (Назва, Class_ID, is_dangerous, rf_params, sound_params)
    signatures_data = [
        # DJI Mavic 3
        (
            "DJI Mavic 3",
            1,
            True,
            ["2400000000-2483500000", "5725000000-5850000000"],
            [],
        ),
        ("DJI Mavic 3", 1, True, [], [450, 600]),
        # Shahed-136
        ("Shahed-136", 2, True, ["1575420000-1575420000", "1227600000-1227600000"], []),
        ("Shahed-136", 2, True, [], [60, 95]),
        # FPV Drone
        ('FPV Drone 7"', 3, True, ["915000000-928000000", "5650000000-5900000000"], []),
        ('FPV Drone 7"', 3, True, [], [850, 1100]),
        # Orlan-10
        ("Orlan-10", 4, True, ["433000000-440000000", "900000000-920000000"], []),
        ("Orlan-10", 4, True, [], [130, 170]),
        # False Alarms
        ("Crow (Ворона)", 5, False, [], [1200, 1600]),
        ("Gas Mower (Косарка)", 5, False, [], [80, 120]),
        ("Public WiFi Hotspot", 6, False, ["2400000000-2483000000"], []),
        ("GSM 900 Link", 6, False, ["935000000-960000000"], []),
    ]

    logger.info("Початок наповнення бази даних")

    for class_name in classes_to_add:
        logger.debug(f"Додавання класу: {class_name}")
        db.add_class(ObjectClass(id=None, name=class_name))
        time.sleep(0.1)

    time.sleep(1)  # Затримка для завершення транзакцій перед додаванням об'єктів

    for name, c_id, dangerous, rf, sound in signatures_data:
        logger.debug(f"Додавання сигнатури: {name}")

        obj = DetectionObject(
            id=None,
            name=name,
            class_id=c_id,
            object_class="",  # Поле буде автоматично заповнене сервісом БД
            is_dangerous=dangerous,
            rf_params_hz=rf,
            sound_params_hz=sound,
        )

        db.add_object(obj)
        time.sleep(0.1)

    logger.info("Наповнення бази даних завершено. Завершення через 2 секунди...")
    QTimer.singleShot(2000, loop.quit)
    loop.exec()


if __name__ == "__main__":
    run_seeding()
