from PyQt6.QtCore import QDateTime, QObject, QTimer, pyqtSignal

from app.protocols import JammerServiceSettings
from app.services.pi_network_service import PiNetworkService


class JammerService(QObject):
    """
    Сервіс керування апаратними реле (Jammer) для придушення сигналів.

    Цей сервіс є посередником між інтерфейсом користувача та мережевим рівнем,
    забезпечуючи логіку активації реле на Raspberry Pi. Він відстежує час роботи,
    керує автоматичним вимкненням (якщо налаштовано) та сповіщає систему про зміну стану.

    Attributes:
        state_changed (pyqtSignal): Сигнал, що випромінюється при зміні стану (bool: True - увімкнено, False - вимкнено).
    """

    state_changed = pyqtSignal(bool)

    def __init__(
        self, pi_network: PiNetworkService, settings_service: JammerServiceSettings
    ) -> None:
        """
        Ініціалізує сервіс керування реле.

        Args:
            pi_network (PiNetworkService): Сервіс мережевої взаємодії для відправки команд на Pi.
            settings_service (JammerServiceSettings): Об'єкт налаштувань, що містить параметри
                автостопу та перелік активних реле.
        """
        super().__init__()
        self.pi_network = pi_network
        self.settings = settings_service
        self.is_active = False
        self.start_time: QDateTime | None = None

        # Таймер використовується для автоматичного припинення випромінювання,
        # щоб запобігти перегріву обладнання або надмірному енергоспоживанню.
        self.auto_stop_timer = QTimer()
        self.auto_stop_timer.setSingleShot(True)
        self.auto_stop_timer.timeout.connect(self.stop)

    def start(self) -> None:
        """
        Активує реле (Jammer).

        Надсилає запит на сервер для замикання реле, запускає таймер авто-стопу
        (якщо це дозволено в налаштуваннях) та фіксує час початку сесії.
        """
        if self.is_active:
            return

        self.is_active = True
        self.start_time = QDateTime.currentDateTime()

        # Надсилаємо список реле, визначених як "основні" для Jammer-а.
        self.pi_network.request_alarm_start(self.settings.main_relays)

        if self.settings.is_jammer_auto_stop_enabled:
            msec = int(self.settings.jammer_auto_stop_interval_s * 1000)
            self.auto_stop_timer.start(msec)

        self.state_changed.emit(True)

    def stop(self) -> None:
        """
        Деактивує реле (Jammer).

        Надсилає запит на розмикання реле, зупиняє активні таймери та
        скидає стан сесії.
        """
        if not self.is_active:
            return

        self.is_active = False
        self.start_time = None

        self.pi_network.request_alarm_stop()

        if self.auto_stop_timer.isActive():
            self.auto_stop_timer.stop()

        self.state_changed.emit(False)

    def update_auto_stop(self) -> None:
        """
        Оновлює параметри таймера авто-стопу на основі нових налаштувань.

        Цей метод дозволяє змінити інтервал авто-стопу "на льоту". Він перераховує
        залишок часу, виходячи з моменту запуску сесії та нових значень у налаштуваннях.
        Якщо новий інтервал вже минув, реле негайно вимикається.
        """

        if not self.is_active or self.start_time is None:
            return

        if self.settings.is_jammer_auto_stop_enabled:
            # Обчислюємо скільки секунд залишилося до вимкнення.
            sec = self.settings.jammer_auto_stop_interval_s - self.start_time.secsTo(
                QDateTime.currentDateTime()
            )
            if sec <= 0:
                self.stop()
                return

            msec = sec * 1000
            self.auto_stop_timer.start(msec)
        elif self.auto_stop_timer.isActive():
            # Якщо авто-стоп було вимкнено в налаштуваннях під час роботи,
            # зупиняємо таймер, щоб сесія тривала до ручної зупинки.
            self.auto_stop_timer.stop()

    def get_formatted_time(self) -> str:
        """
        Повертає тривалість поточної сесії роботи у форматі HH:MM:SS.

        Цей метод використовується переважно для відображення таймера в інтерфейсі.

        Returns:
            str: Відформатований рядок часу (наприклад, "00:05:30").
        """

        if self.start_time is None or not self.is_active:
            return "00:00:00"

        secs = self.start_time.secsTo(QDateTime.currentDateTime())
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h:02}:{m:02}:{s:02}"
