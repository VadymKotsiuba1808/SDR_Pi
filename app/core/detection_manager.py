from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from app.core.logging_config import get_logger
from app.models.detection_event import DetectionEvent
from app.models.radar_target import RadarTarget
from app.protocols import DetectionManagerSettings

logger = get_logger(__name__)


class DetectionManager(QObject):
    """
    Менеджер для управління детекціями радара.

    Цей клас відповідає за відстеження активних цілей, керування їхніми візуальними індексами,
    обробку TTL (Time To Live) та координацію оновлень інтерфейсу.
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

    def _setup_variables(self) -> None:
        self.active_targets: Dict[str, RadarTarget] = {}
        self.index_history: Dict[str, int] = {}
        self.ignored_ids: Dict[str, datetime] = {}
        self.next_index: int = 1
        self.update_requested: bool = False

    def _setup_timers(self) -> None:
        self.ttl_timer: QTimer = QTimer(self)
        self.ttl_timer.timeout.connect(self._check_ttl)
        self.ttl_timer.start(1000)
        logger.debug("TTL timer activated (interval: 1s)")

    def add_detection(self, event: DetectionEvent) -> None:
        if self._is_ignored(event.id):
            return

        if event.id in self.active_targets:
            self.active_targets[event.id].update(event)
            logger.debug("Target updated: ID=%s", event.id)
            self._trigger_update()
            return

        visual_index: int = self._get_visual_index(event.id)
        new_target = RadarTarget(event=event, visual_index=visual_index)

        self.active_targets[event.id] = new_target
        logger.info("New target added: ID=%s, Index=%d", event.id, visual_index)
        self._trigger_update()

    def remove_detection(self, event_id: str) -> None:
        if event_id not in self.active_targets:
            return

        self.ignored_ids[event_id] = datetime.now() + timedelta(seconds=3)
        del self.active_targets[event_id]

        logger.info("Target %s removed manually (ignoring activated)", event_id)

        self._check_cleanup()
        self._trigger_update()

    def clear_detections(self) -> None:
        expiry: datetime = datetime.now() + timedelta(seconds=3)
        count = len(self.active_targets)

        for eid in self.active_targets:
            self.ignored_ids[eid] = expiry

        self.active_targets.clear()
        self.next_index = 1
        self.index_history.clear()

        logger.info("Full detections cleanup performed (%d removed)", count)
        self._trigger_update()

    def _check_ttl(self) -> None:
        ids_to_remove: List[str] = [
            tid
            for tid, target in self.active_targets.items()
            if target.is_expired(self.settings_service.detection_ttl_s)
        ]

        for tid in ids_to_remove:
            del self.active_targets[tid]

        if ids_to_remove:
            logger.debug("Removed by TTL: %d targets", len(ids_to_remove))

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
        if event_id in self.index_history:
            return self.index_history[event_id]

        idx: int = self.next_index
        self.next_index += 1
        self.index_history[event_id] = idx
        return idx

    def _check_cleanup(self) -> None:
        if not self.active_targets:
            self.next_index = 1
            self.index_history.clear()

    def _is_ignored(self, event_id: str) -> bool:
        if event_id in self.ignored_ids:
            if datetime.now() < self.ignored_ids[event_id]:
                return True
            del self.ignored_ids[event_id]
        return False

    def get_targets(self) -> List[RadarTarget]:
        return list(self.active_targets.values())

    def get_target_by_id(self, event_id: str) -> Optional[RadarTarget]:
        return self.active_targets.get(event_id)

    def get_index_by_id(self, event_id: str) -> Optional[int]:
        target: Optional[RadarTarget] = self.active_targets.get(event_id)
        return target.visual_index if target else None

    def has_detections(self) -> bool:
        return bool(self.active_targets)

    def _trigger_update(self) -> None:
        if not self.update_requested:
            self.update_requested = True
            QTimer.singleShot(50, self._emit_debounced)

    def _emit_debounced(self) -> None:
        self.update_requested = False
        self.detections_changed.emit()
