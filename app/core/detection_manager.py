from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from app.models.detection_event import DetectionEvent
from app.models.radar_target import RadarTarget
from app.protocols import DetectionManagerSettings


class DetectionManager(QObject):
    """Менеджер для управління детекціями радара.

    Цей клас відповідає за життєвий цикл виявлених цілей (RadarTarget), включаючи
    їх додавання, оновлення, автоматичне видалення за часом (TTL) та
    керування візуальними індексами для відображення в UI.

    Attributes:
        detections_changed (pyqtSignal): Сигнал, що випромінюється при будь-якій зміні
            списку активних цілей (з використанням дебаунсу).
    """

    detections_changed = pyqtSignal()

    def __init__(
        self,
        settings_service: DetectionManagerSettings,
        parent: Optional[QObject] = None,
    ) -> None:
        """Ініціалізує менеджер детекцій.

        Args:
            settings_service: Сервіс налаштувань для отримання параметрів TTL тощо.
            parent: Батьківський QObject.
        """
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

    def add_detection(self, event: DetectionEvent) -> None:
        """Додає нову детекцію або оновлює існуючу ціль.

        Якщо ціль з таким ID вже існує, її дані оновлюються. Якщо ID знаходиться
        в списку тимчасового ігнорування (наприклад, після видалення користувачем),
        подія ігнорується.

        Args:
            event: Подія детекції, отримана від сервера.
        """

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
        """Видаляє ціль зі списку активних.

        Після видалення ID цілі додається до списку ігнорування на 3 секунди,
        щоб запобігти її негайному повторному додаванню при надходженні
        наступного пакету даних від сервера.

        Args:
            event_id: Унікальний ідентифікатор цілі.
        """
        if event_id not in self.active_targets:
            return

        self.ignored_ids[event_id] = datetime.now() + timedelta(seconds=3)

        del self.active_targets[event_id]

        self._check_cleanup()
        self._trigger_update()

    def clear_detections(self) -> None:
        """Повністю очищує всі активні цілі та історію індексів.

        Всі поточні активні цілі додаються до списку ігнорування на 3 секунди.
        Лічильник візуальних індексів скидається до 1.
        """
        expiry: datetime = datetime.now() + timedelta(seconds=3)

        eid: str
        for eid in self.active_targets:
            self.ignored_ids[eid] = expiry

        self.active_targets.clear()

        self.next_index = 1
        self.index_history.clear()

        self._trigger_update()

    def _check_ttl(self) -> None:
        """Перевіряє цілі на застарілість та очищує список ігнорування.

        Ціль вважається застарілою, якщо час з моменту її останнього оновлення
        перевищує `detection_ttl_s` з налаштувань. Також видаляє ID зі списку
        ігнорування, якщо час ігнорування вичерпано.
        """
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
        """Визначає візуальний індекс для цілі.

        Якщо ціль вже мала індекс раніше (є в історії), повертає його.
        В іншому випадку створює новий індекс, інкрементуючи лічильник.

        Args:
            event_id: ID події.

        Returns:
            Візуальний індекс (ціле число).
        """
        if event_id in self.index_history:
            return self.index_history[event_id]

        idx: int = self.next_index
        self.next_index += 1
        self.index_history[event_id] = idx
        return idx

    def _check_cleanup(self) -> None:
        """Скидає стан індексації, якщо немає активних цілей.

        Це дозволяє починати нумерацію цілей з 1, коли моніторинг відновлюється
        після повної відсутності об'єктів.
        """
        if not self.active_targets:
            self.next_index = 1
            self.index_history.clear()

    def _is_ignored(self, event_id: str) -> bool:
        """Перевіряє, чи ігнорується даний ID.

        Args:
            event_id: ID для перевірки.

        Returns:
            True, якщо ID ігнорується, інакше False.
        """
        if event_id in self.ignored_ids:
            if datetime.now() < self.ignored_ids[event_id]:
                return True
            else:
                del self.ignored_ids[event_id]
        return False

    def get_targets(self) -> List[RadarTarget]:
        """Повертає список всіх поточних активних цілей.

        Returns:
            Список об'єктів RadarTarget.
        """
        return list(self.active_targets.values())

    def get_target_by_id(self, event_id: str) -> Optional[RadarTarget]:
        """Шукає активну ціль за її ідентифікатором.

        Args:
            event_id: ID цілі.

        Returns:
            Об'єкт RadarTarget або None, якщо ціль не знайдена.
        """
        return self.active_targets.get(event_id)

    def get_index_by_id(self, event_id: str) -> Optional[int]:
        """Повертає візуальний індекс цілі за її ID.

        Args:
            event_id: ID цілі.

        Returns:
            Індекс або None, якщо ціль не активна.
        """
        target: Optional[RadarTarget] = self.active_targets.get(event_id)
        return target.visual_index if target else None

    def has_detections(self) -> bool:
        """Перевіряє наявність активних цілей.

        Returns:
            True, якщо є хоча б одна активна ціль.
        """
        return bool(self.active_targets)

    def _trigger_update(self) -> None:
        """Ініціює випромінювання сигналу про зміну детекцій з дебаунсом.

        Використовується для оптимізації продуктивності UI, щоб уникнути
        занадто частого перемалювання при масовому надходженні оновлень.
        """
        if not self.update_requested:
            self.update_requested = True
            QTimer.singleShot(50, self._emit_debounced)

    def _emit_debounced(self) -> None:
        """Випромінює сигнал `detections_changed` після затримки дебаунсу."""
        self.update_requested = False
        self.detections_changed.emit()
