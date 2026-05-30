from PyQt6.QtCore import QDateTime, QObject, QTimer, pyqtSignal

from app.protocols import JammerServiceSettings
from app.services.pi_network_service import PiNetworkService


class JammerService(QObject):
    state_changed = pyqtSignal(bool)

    def __init__(
        self, pi_network: PiNetworkService, settings_service: JammerServiceSettings
    ):
        super().__init__()
        self.pi_network = pi_network
        self.settings = settings_service
        self.is_active = False
        self.start_time = None

        self.auto_stop_timer = QTimer()
        self.auto_stop_timer.setSingleShot(True)
        self.auto_stop_timer.timeout.connect(self.stop)

    def start(self):
        if self.is_active:
            return

        self.is_active = True
        self.start_time = QDateTime.currentDateTime()

        self.pi_network.request_alarm_start(self.settings.main_relays)

        if self.settings.is_jammer_auto_stop_enabled:
            msec = self.settings.jammer_auto_stop_interval_s * 1000
            self.auto_stop_timer.start(msec)

        self.state_changed.emit(True)

    def stop(self):
        if not self.is_active:
            return

        self.is_active = False
        self.start_time = None

        self.pi_network.request_alarm_stop()

        if self.auto_stop_timer.isActive():
            self.auto_stop_timer.stop()

        self.state_changed.emit(False)

    def update_auto_stop(self):

        if not self.is_active or self.start_time is None:
            return

        if self.settings.is_jammer_auto_stop_enabled:
            sec = self.settings.jammer_auto_stop_interval_s - self.start_time.secsTo(
                QDateTime.currentDateTime()
            )
            if sec <= 0:
                self.stop()
                return

            msec = sec * 1000
            self.auto_stop_timer.start(msec)
        elif self.auto_stop_timer.isActive():
            self.auto_stop_timer.stop()

    def get_formatted_time(self) -> str:

        if self.start_time is None or not self.is_active:
            return "00:00:00"

        secs = self.start_time.secsTo(QDateTime.currentDateTime())
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h:02}:{m:02}:{s:02}"
