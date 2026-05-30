from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from app.models.detection_event import DetectionEvent
from app.models.radar_target import RadarTarget
from app.protocols import DetectionManagerSettings


class DetectionManager(QObject):
    """
    Менеджер для управління детекціями: додавання, видалення, TTL, індексація.
    """

    detections_changed = pyqtSignal()

    def __init__(
        self,
        settings_service: DetectionManagerSettings,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.settings_service = settings_service

        self._setup_variables()
        self._setup_timers()

    def _setup_variables(self):
        self.active_targets: Dict[str, RadarTarget] = {}

        self.index_history: Dict[str, int] = {}

        self.ignored_ids: Dict[str, datetime] = {}

        self.next_index: int = 1

        self.update_requested: bool = False

    def _setup_timers(self):
        self.ttl_timer: QTimer = QTimer(self)
        self.ttl_timer.timeout.connect(self._check_ttl)
        self.ttl_timer.start(1000)

    def add_detection(self, event: DetectionEvent) -> None:
        """Головний метод додавання або оновлення цілі."""

        if self._is_ignored(event.id):
            return

        if event.id in self.active_targets:
            self.active_targets[event.id].update(event)
            self._trigger_update()
            return

        visual_index: int = self._get_visual_index(event.id)

        new_target = RadarTarget(event=event, visual_index=visual_index)

        self.active_targets[event.id] = new_target
        self._trigger_update()

    def remove_detection(self, event_id: str) -> None:
        """Ручне видалення цілі (наприклад, кнопкою 'False Alarm')."""
        if event_id not in self.active_targets:
            return

        self.ignored_ids[event_id] = datetime.now() + timedelta(seconds=3)

        del self.active_targets[event_id]

        self._check_cleanup()
        self._trigger_update()

    def clear_detections(self) -> None:
        """Повне очищення всіх детекцій."""
        expiry: datetime = datetime.now() + timedelta(seconds=3)

        eid: str
        for eid in self.active_targets:
            self.ignored_ids[eid] = expiry

        self.active_targets.clear()

        self.next_index = 1
        self.index_history.clear()

        self._trigger_update()

    def _check_ttl(self) -> None:
        """Періодична перевірка на застарілі дані."""
        ids_to_remove: List[str] = [
            tid
            for tid, target in self.active_targets.items()
            if target.is_expired(self.settings_service.detection_ttl_s)
        ]

        tid: str
        for tid in ids_to_remove:
            del self.active_targets[tid]

        now: datetime = datetime.now()
        expired_ignores: List[str] = [
            tid for tid, exp in self.ignored_ids.items() if now > exp
        ]

        for tid in expired_ignores:
            del self.ignored_ids[tid]

        if ids_to_remove:
            self._check_cleanup()
            self._trigger_update()

    def _get_visual_index(self, event_id: str) -> int:
        """Логіка вибору індексу: повертає старий з історії або створює новий."""
        if event_id in self.index_history:
            return self.index_history[event_id]

        idx: int = self.next_index
        self.next_index += 1
        self.index_history[event_id] = idx
        return idx

    def _check_cleanup(self) -> None:
        """Якщо активних цілей не залишилось, скидаємо лічильник індексів."""
        if not self.active_targets:
            self.next_index = 1
            self.index_history.clear()

    def _is_ignored(self, event_id: str) -> bool:
        """Перевіряє, чи знаходиться ID в списку ігнорування."""
        if event_id in self.ignored_ids:
            if datetime.now() < self.ignored_ids[event_id]:
                return True
            else:
                del self.ignored_ids[event_id]
        return False

    def get_targets(self) -> List[RadarTarget]:
        """Повертає список всіх активних об'єктів (для малювання)."""
        return list(self.active_targets.values())

    def get_target_by_id(self, event_id: str) -> Optional[RadarTarget]:
        """Пошук конкретного об'єкта за ID (для обробки кліків)."""
        return self.active_targets.get(event_id)

    def get_index_by_id(self, event_id: str) -> Optional[int]:
        """Повертає візуальний індекс за ID події."""
        target: Optional[RadarTarget] = self.active_targets.get(event_id)
        return target.visual_index if target else None

    def has_detections(self) -> bool:
        """Перевірка на наявність будь-яких цілей."""
        return bool(self.active_targets)

    def _trigger_update(self) -> None:
        if not self.update_requested:
            self.update_requested = True
            QTimer.singleShot(50, self._emit_debounced)

    def _emit_debounced(self) -> None:
        self.update_requested = False
        self.detections_changed.emit()
