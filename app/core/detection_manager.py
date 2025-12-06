"""
Менеджер для управління детекціями: додавання, видалення, TTL, індексація.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from app.models.detection_event import DetectionEvent
from datetime import datetime, timedelta  #


class DetectionManager(QObject):
    detections_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_detections = {}
        self.detection_indices = {}

        self.ignored_detections = {}

        self.next_index = 1
        self.update_requested = False
        self.ttl_timer = QTimer(self)
        self.ttl_timer.timeout.connect(self._check_ttl)
        self.ttl_timer.start(3000)
        self.ttl_seconds = 30

    def add_detection(self, event: DetectionEvent):
        event_id = event.id

        if event_id in self.ignored_detections:
            expiry_time = self.ignored_detections[event_id]
            if datetime.now() < expiry_time:
                return
            else:
                del self.ignored_detections[event_id]
        # ---------------------------

        if event_id in self.current_detections:
            self.current_detections[event_id] = event
            self._trigger_update()
            return

        self.current_detections[event_id] = event
        self.detection_indices[event_id] = self.next_index
        self.next_index += 1
        self._trigger_update()

    def remove_detection(self, event_id):
        if event_id not in self.current_detections:
            return

        # Додаємо ID в список ігнорування на 3 секунди вперед
        self.ignored_detections[event_id] = datetime.now() + timedelta(seconds=3)

        del self.current_detections[event_id]
        del self.detection_indices[event_id]

        if not self.current_detections:
            self.next_index = 1

        self._trigger_update()

    def _check_ttl(self):
        now = datetime.now()

        to_remove = [
            eid
            for eid, event in self.current_detections.items()
            if (now - datetime.fromisoformat(event.timestamp)).total_seconds()
            > self.ttl_seconds
        ]
        for eid in to_remove:
            del self.current_detections[eid]
            del self.detection_indices[eid]

        if to_remove:
            if not self.current_detections:
                self.next_index = 1
            self._trigger_update()

        ignored_to_remove = [
            eid for eid, expiry in self.ignored_detections.items() if now > expiry
        ]
        for eid in ignored_to_remove:
            del self.ignored_detections[eid]

    def clear_detections(self):
        expiry = datetime.now() + timedelta(seconds=3)
        for eid in self.current_detections:
            self.ignored_detections[eid] = expiry

        self.current_detections.clear()
        self.detection_indices.clear()
        self.next_index = 1
        self._trigger_update()

    def get_detections(self):
        return self.current_detections, self.detection_indices

    def has_detections(self):
        return bool(self.current_detections)

    def _trigger_update(self):
        if not self.update_requested:
            self.update_requested = True
            QTimer.singleShot(50, self._emit_debounced)

    def _emit_debounced(self):
        self.update_requested = False
        self.detections_changed.emit()
