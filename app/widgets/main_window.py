import os
import math
import asyncio
from typing import Optional, List, Dict, Any, cast

from PyQt6.QtWidgets import (
    QMainWindow,
    QDialog,
    QMessageBox,
    QFileDialog,
    QWidget,
    QPushButton,
    QDoubleSpinBox,
    QLineEdit,
)
from PyQt6.QtCore import (
    QTimer,
    QTime,
    QDateTime,
    Qt,
    QPointF,
    QEvent,
    QCoreApplication,
    QTranslator,
    pyqtSlot,
    pyqtSignal,
    QUrl,
)
from PyQt6.QtGui import (
    QPixmap,
    QConicalGradient,
    QPainter,
    QColor,
    QPen,
    QDesktopServices,
    QFont,
    QShowEvent,
    QCloseEvent,
)
from PyQt6 import uic
from qasync import asyncSlot


from app.ui.ui_main_window import Ui_MainWindow
from app.assets import resources_rc


from app.protocols import OSService


from app.widgets.set_map_dialog import SetMapDialog
from app.widgets.autosize_window import make_scalable
from app.widgets.log_dialog import LogDialog
from app.widgets.record_status_widget import RecordingStatusWidget
from app.widgets.object_manager_dialog import ObjectManagerDialog
from app.widgets.settings_dialog import SettingsDialog


from app.services.pi_network_service import PiNetworkService
from app.services.settings_service import SettingsService
from app.services.map_service import MapService, MapTypes
from app.services.keyboard_service import KeyboardService
from app.services.recording_service import RecordingService
from app.services.media_player_service import MediaPlayerService
from app.services.database_service import DatabaseService
from app.services.log_service import LogService


from app.core.detection_manager import DetectionManager
from app.models.detection_event import DetectionEvent
from app.models.log_entries import LogEntry, LogType, FalseAlarmPayload


from app.utils.ui_utils import update_element_styles, move_dialog_down
from app.utils.system_utils import (
    get_wifi_signal_strength,
    restart_process,
)


MIN_DISTANCE_THRESHOLD = 2.0  # Мінімальна зміна позиції в метрах для оновлення мапи
DEFAULT_START_COORDS = [49.43440, 27.00543]

TIMER_INTERVAL_TIME_UPDATE = 1 * 1000
TIMER_INTERVAL_RADAR_ANIM = 60
TIMER_INTERVAL_WIFI_UPDATE = 30 * 1000

SIGNAL_LEVEL_COUNT = 4


class MainWindow(QMainWindow):
    """
    Головне вікно програми (Controller).
    Зв'язує графічний інтерфейс (View) з сервісами та логікою.
    Обробляє навігацію та глобальні події.
    """

    _sig_start_recording = pyqtSignal(str)
    _sig_stop_recording = pyqtSignal()

    def __init__(
        self,
        settings: SettingsService,
        keyboard: KeyboardService,
        system: OSService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.settings_service = settings
        self.system_service = system
        self.keyboard_service = keyboard

        self._load_ui()
        print("[MainWindow] Interface loaded.")

        self._setup_state_variables()
        self._init_recording_service()
        self._adjust_fields()
        self._connect_handlers()
        self._setup_timers()

        self.update_wifi_signal_info()
        self.change_language()

        self.update_gps_and_map()
        self._start_async_tasks()

        self.refresh_map()

        print("[MainWindow] Initialization complete.")

    # region --- Init ---
    def showEvent(self, event: QShowEvent) -> None:

        super().showEvent(event)
        # self.ui.map_background_label.setScaledContents(False)

        self.radar_clean_pixmap = QPixmap(":/images/radar.png").scaled(
            self.ui.Radar.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def resizeEvent(self, event) -> None:
        self._update_map_geometry()
        super().resizeEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("[MainWindow] Language change detected, updating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/main_window.ui", self)
            self.ui = self

    def _setup_state_variables(self) -> None:

        self.map_service = MapService(settings=self.settings_service)

        # Індекс об'єкта, який зараз шукається/відображається
        self.searched_index: Optional[int] = None

        # Менеджер детекцій
        self.detection_manager = DetectionManager(self)
        self.detection_manager.detections_changed.connect(self._update_detection_ui)

        # Мережевий сервіс (Pi)
        self.pi_network = PiNetworkService(self.settings_service, self)
        self.pi_network.data_received.connect(self.handle_pi_data)
        self.pi_network.gps_received.connect(self.handle_gps)
        self.pi_network.detection_received.connect(self.handle_detection)
        self.pi_network.rf_data_received.connect(self.handle_rf_data)
        self.pi_network.sound_data_received.connect(self.handle_sound_data)

        # Сервіс бази даних (через мережу)
        self.db_service = DatabaseService(self.pi_network)

        self.log_service = LogService()

        # Змінні карти
        self.current_map_type_index: int = 0
        self.map_types: List[MapTypes] = [e for e in MapTypes]
        self.current_coords: List[float] = DEFAULT_START_COORDS
        self.current_map: Optional[QPixmap] = None
        self.add_sizes_map_k: List[float] = [1.0, 1.0]
        self.current_map_resolution: float = 1.0

        # UI Стани
        self.is_radar_mode: bool = False
        self.is_alert: bool = False
        self.radar_angle: int = 0
        self.force_gps_update: bool = False
        self.is_jammer_active: bool = False

        self.jammer_start_time: QDateTime = None
        self.jammer_stop_timer: QTimer = None

        if self.settings_service.is_jammer_auto_stop_enabled:
            self.jammer_stop_timer = QTimer(self)
            self.jammer_stop_timer.setSingleShot(True)
            self.jammer_stop_timer.timeout.connect(self.stop_jammer)

        self.translator = QTranslator()

        self.record_status_widget = RecordingStatusWidget(self.settings_service, self)

        self.media_service = MediaPlayerService(self.system_service)
        self.media_service.playback_finished.connect(
            lambda: self.ui.filesViewButton.setChecked(False)
        )

    def _init_recording_service(self) -> None:
        self.recorder = RecordingService(self.system_service, self)

        self.recorder.recording_started.connect(self.on_recording_started)
        self.recorder.recording_stopped.connect(self.on_recording_stopped)
        self.recorder.recording_error.connect(self.show_error_message)
        self.recorder.duration_updated.connect(
            self.record_status_widget.update_duration
        )
        self.recorder.recording_paused.connect(
            self.record_status_widget.on_pause_toggled
        )

    def _adjust_fields(self) -> None:
        radar_max_radius = self.settings_service.radar_max_radius
        self.ui.radarRadiusSpinbox.setMaximum(radar_max_radius)

        radar_radius = self.settings_service.radar_radius
        self.ui.radarRadiusSpinbox.setValue(radar_radius)

        radio_range = self.settings_service.radio_range_GHz
        self.ui.radioStartDoubleSpinBox.setValue(float(radio_range[0]))
        self.ui.radioEndDoubleSpinBox.setValue(float(radio_range[1]))

        current_lang = self.settings_service.lang_code
        self.ui.langComboBox.setCurrentIndex(1 if current_lang == "en" else 0)

        role = self.settings_service.role
        if role != "owner":
            self.ui.falseAlarmButton.setVisible(False)
            self.ui.menuButton.setVisible(False)
            self.ui.backToLoginButton.setVisible(True)
        else:
            self.ui.backToLoginButton.setVisible(False)

        self.ui.screenRecordingLayout.addWidget(self.record_status_widget)

    def _connect_handlers(self) -> None:
        self.ui.mapLayoutButton.clicked.connect(self.change_map_type)
        self.ui.screenSaveButton.clicked.connect(self.take_screenshot)
        self.ui.homeButton.clicked.connect(self.update_gps_and_map)
        self.ui.addMapButton.clicked.connect(self.handle_add_map)
        self.ui.screenRecordButton.clicked.connect(self.handle_toggle_recording)
        self.ui.filesViewButton.clicked.connect(self.handle_open_file)
        self.ui.viewObjectButton.clicked.connect(self.open_database_manager)
        self.ui.viewLogsButton.clicked.connect(self.open_logs_dialog)

        self.ui.falseAlarmButton.clicked.connect(self.handle_false_alarm)
        self.ui.menuButton.clicked.connect(self.open_settings_dialog)
        self.ui.radarButton.clicked.connect(self.set_radar_mode)
        self.ui.mapButton.clicked.connect(self.set_map_mode)
        self.ui.backToLoginButton.clicked.connect(self.restart_app)

        self.ui.saveRadarSettingsBtn.clicked.connect(self.handle_radar_radius_change)
        self.ui.index_search_edit.returnPressed.connect(self.perform_search)

        self.ui.saveRadioRangePushButton.clicked.connect(self.set_radio_range)
        self.ui.clearRadioRangePushButton.clicked.connect(self.clear_radio_range_values)
        self.ui.chartRangePushButton.clicked.connect(self.open_range_chart_dialog)

        self.ui.radioStartDoubleSpinBox.valueChanged.connect(
            self.handle_signal_range_change
        )
        self.ui.radioEndDoubleSpinBox.valueChanged.connect(
            self.handle_signal_range_change
        )

        self.ui.langComboBox.currentIndexChanged.connect(self.change_language)

        self.record_status_widget.ui.pause_button.toggled.connect(
            self.handle_toggle_recording_pause
        )

        self.ui.jammerOnTimerButton.clicked.connect(self.start_jammer)
        self.ui.jammerOffTimerButton.clicked.connect(self.stop_jammer)

    def _setup_timers(self) -> None:
        self.timer_1sec = QTimer(self)
        self.timer_1sec.timeout.connect(self.update_time_and_date)
        self.timer_1sec.start(TIMER_INTERVAL_TIME_UPDATE)

        self.timer_radar = QTimer(self)
        self.timer_radar.timeout.connect(self.rotate_radar_animation)
        self.timer_radar.start(TIMER_INTERVAL_RADAR_ANIM)

        self.timer_wifi = QTimer(self)
        self.timer_wifi.timeout.connect(self.update_wifi_signal_info)
        self.timer_wifi.start(TIMER_INTERVAL_WIFI_UPDATE)

        self.timer_gps = QTimer(self)
        self.timer_gps.timeout.connect(self.request_gps)
        self.timer_gps.start(self.settings_service.gps_interval_s * 1000)

    @asyncSlot()
    async def _start_async_tasks(self) -> None:
        """
        Запускає всі фонові асинхронні задачі.
        """
        print("[MainWindow] Starting async background tasks (network)...")
        self.pi_network.start()

    def _update_map_geometry(self) -> None:
        if not self.ui.RadarFrame.width() or not self.ui.RadarFrame.height():
            return

        radar_rect = self.ui.RadarFrame.geometry()
        bg_width = self.ui.map_background_label.parent().width()
        bg_height = self.ui.map_background_label.parent().height()

        rx = radar_rect.center().x()
        ry = radar_rect.center().y()

        max_dist_x = max(rx, bg_width - rx)
        max_dist_y = max(ry, bg_height - ry)

        radar_radius_px = radar_rect.width() / 2.0
        if radar_radius_px <= 0:
            return

        k_w = max_dist_x / radar_radius_px
        k_h = max_dist_y / radar_radius_px

        self.add_sizes_map_k = [k_w * 1.05, k_h * 1.05]

    def load_language(self) -> None:
        lang_code = self.settings_service.lang_code

        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"[MainWindow] Error: Failed to load translation file: {path}")

    def change_language(self) -> None:
        index = self.ui.langComboBox.currentIndex()
        new_lang_code = "en" if index == 1 else "uk"

        self.settings_service.lang_code = new_lang_code
        print(f"[MainWindow] Language changed to: {new_lang_code}")

        if self.settings_service.compiled_ui_using_enabled:
            self.load_language()

    # endregion

    # region --- Data Handlers ---

    def handle_rf_data(self, data: Dict[str, Any]) -> None:
        """Заглушка для обробки потокових RF-даних."""
        pass  # Логіка буде додана пізніше

    def handle_sound_data(self, data: Dict[str, Any]) -> None:
        """Заглушка для обробки потокових звукових даних."""
        pass  # Логіка буде додана пізніше

    def handle_detection(self, detection: DetectionEvent):
        self.detection_manager.add_detection(detection)

        log = LogEntry(LogType.DETECTION, detection)
        self.log_service.add_log(log)

    @pyqtSlot()
    def _update_detection_ui(self) -> None:
        self.update_radar()
        self.update_detection_info()
        self.update_alert_status()

    def update_radar(self) -> None:
        RADAR_POINT_SIZE = 20
        RADAR_TEXT_OFFSET_Y_DEFAULT = -15
        RADAR_TEXT_OFFSET_CORRECTION = 15
        RADAR_BORDER_OFFSET = 15
        RADAR_ANGLE_ROTATION_OFFSET = 90

        RADAR_TEXT_ANGLE_THRESHOLD_LOW = 40
        RADAR_TEXT_ANGLE_THRESHOLD_HIGH = 320

        detections, indices = self.detection_manager.get_detections()

        if hasattr(self, "radar_clean_pixmap"):
            pixmap = self.radar_clean_pixmap.copy()
        else:
            return

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)

        center_x = pixmap.width() / 2
        center_y = pixmap.height() / 2

        offset_x = 0
        offset_y = RADAR_TEXT_OFFSET_Y_DEFAULT

        max_px_radius = min(center_x, center_y)

        max_meters_setting = self.settings_service.radar_radius
        if max_meters_setting <= 0:
            max_meters_setting = 1

        scale = max_px_radius / max_meters_setting

        for event_id, event in detections.items():
            index = str(indices.get(event_id, "?"))

            pixel_dist = event.distance * scale

            is_out_of_bounds = pixel_dist > max_px_radius
            is_on_border = pixel_dist >= max_px_radius - RADAR_POINT_SIZE / 2

            if is_out_of_bounds or is_on_border:
                pixel_dist = max_px_radius - RADAR_BORDER_OFFSET

                if (
                    event.angle > RADAR_TEXT_ANGLE_THRESHOLD_HIGH
                    or event.angle < RADAR_TEXT_ANGLE_THRESHOLD_LOW
                ):
                    offset_y = 0
                    offset_x = RADAR_TEXT_OFFSET_CORRECTION

            if is_out_of_bounds:
                painter.setPen(QPen(QColor("orange"), RADAR_POINT_SIZE - 2))
            else:
                color = QColor("red")
                painter.setPen(QPen(color, RADAR_POINT_SIZE))

            rad_angle = math.radians(event.angle - RADAR_ANGLE_ROTATION_OFFSET)

            x = center_x + pixel_dist * math.cos(rad_angle)
            y = center_y + pixel_dist * math.sin(rad_angle)

            painter.drawPoint(int(x), int(y))

            painter.setPen(QPen(QColor("black"), 1))
            painter.drawText(int(x) + offset_x, int(y) + offset_y, index)

        painter.end()
        self.ui.Radar.setPixmap(pixmap)

    def update_detection_info(self) -> None:
        if self.searched_index is None:
            self.ui.detection_info_text.clear()
            return

        target_event = self.find_event_by_searched_index()

        if target_event:
            info = (
                f"INDEX: {self.searched_index}\n"
                f"----------------------\n"
                f"TYPE:    {target_event.type}\n"
                f"NAME:    {target_event.name.upper()}\n"
                f"CLASS:   {target_event.object_class.upper()}\n"
                f"DIST:    {target_event.distance} m\n"
                f"ANGLE:   {target_event.angle:.1f}°\n"
                f"CONF:    {target_event.confidence * 100:.1f}%\n"
                f"TIME:    {target_event.timestamp.split('T')[-1][:8]}\n"
            )
            self.ui.detection_info_text.setPlainText(info)
        else:
            self.ui.detection_info_text.setPlainText(
                f"INDEX {self.searched_index}: \n\n[OFFLINE] / [NOT FOUND]\n\n"
                "Target lost or not yet detected."
            )

    def find_event_by_searched_index(self) -> Optional[DetectionEvent]:
        detections, indices = self.detection_manager.get_detections()

        for eid, idx in indices.items():
            if idx == self.searched_index:
                return detections.get(eid)

        return None

    def update_alert_status(self) -> None:
        detections, _ = self.detection_manager.get_detections()

        has_rf = any(e.type == "RF" for e in detections.values())
        has_sound = any(e.type == "Sound" for e in detections.values())

        self.ui.RF_alert.setProperty("alert", has_rf)
        self.ui.Sound_alert.setProperty("alert", has_sound)
        update_element_styles(self.ui.RF_alert)
        update_element_styles(self.ui.Sound_alert)

        self.ui.falseAlarmButton.setEnabled(self.detection_manager.has_detections())

    def handle_false_alarm(self) -> None:
        target_event = self.find_event_by_searched_index()
        if target_event:
            self.pi_network.report_false_alarm(target_event.id)
            self.detection_manager.remove_detection(target_event.id)

            payload = FalseAlarmPayload(target_event.id, target_event.name)
            log = LogEntry(LogType.FALSE_ALARM, payload)
            self.log_service.add_log(log)

    # endregion

    # region --- GPS & Map ---

    def request_gps(self) -> None:
        self.pi_network.request_remote_gps()

    def update_gps_ui(self, data: Dict[str, Any]) -> None:
        strength = data.get("gps_strength")
        lat = data.get("gps_lat")
        lon = data.get("gps_lon")

        if not lat or not lon:
            self.set_gps_ui_level(0)
            return

        new_lat, new_lon = float(lat), float(lon)
        distance = self.calculate_distance(
            self.current_coords[0], self.current_coords[1], new_lat, new_lon
        )
        if distance >= MIN_DISTANCE_THRESHOLD or self.force_gps_update:
            self.current_coords = [new_lat, new_lon]
            self.refresh_map()
            self.force_gps_update = False
            print(f"[MainWindow] Map refreshed. Distance moved: {distance:.2f} m")
        else:
            print(
                f"[MainWindow] Update skipped. Distance change too small: {distance:.2f} m"
            )

        print(f"GPS Signal Strength: {strength}")

        gps_level = 0
        if strength:
            gps_level = math.ceil(strength / (100 / SIGNAL_LEVEL_COUNT))

        self.set_gps_ui_level(gps_level)

    def calculate_distance(self, lat1, lon1, lat2, lon2):

        R = 6371000  # Радіус Землі в метрах
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def set_gps_ui_level(self, level: int) -> None:
        self.ui.GPS_level.setProperty("level", level)
        update_element_styles(self.ui.GPS_level)

    @pyqtSlot(dict)
    def handle_gps(self, data: Dict[str, Any]) -> None:
        self.update_gps_ui(data)
        print(
            f"[MainWindow] GPS Received: {data.get('gps_lat')}, {data.get('gps_lon')}"
        )

    def handle_radar_radius_change(self) -> None:
        new_radar_radius = self.ui.radarRadiusSpinbox.value()
        self.settings_service.radar_radius = new_radar_radius

        self.scale_map()
        self.update_radar()

    def handle_add_map(self) -> None:
        btn = cast(QPushButton, self.sender())

        if not btn.isChecked():
            asyncio.create_task(self.refresh_map())
            return

        self.open_set_map_dialog()

    def open_set_map_dialog(self) -> None:
        self.dialog = SetMapDialog(
            settings=self.settings_service, add_sizes_map_k=self.add_sizes_map_k
        )

        ScalableDialog = make_scalable(QDialog)
        self.scalable_dialog = ScalableDialog(widget_to_scale=self.dialog)

        result = self.scalable_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            settings_data = self.scalable_dialog.get_settings()

            if settings_data.get("pixmap"):
                self.current_map = settings_data["pixmap"]
                print(f"[MainWindow] Custom map set. Width: {self.current_map.width()}")

                radar_max_radius = self.settings_service.radar_max_radius

                self.scale_map()

            print("[MainWindow] Map settings applied.")
        else:
            self.ui.addMapButton.setChecked(False)
            print("[MainWindow] Map settings cancelled.")

        self.scalable_dialog = None

    # endregion

    # region --- Dialogs ---

    def open_database_manager(self) -> None:
        self.db_window = ObjectManagerDialog(
            self.db_service, self.settings_service, self.keyboard_service
        )
        move_dialog_down(self.db_window, self.geometry())
        self.db_window.exec()

    def open_logs_dialog(self) -> None:
        logs_dialog = LogDialog(self.log_service, self.settings_service)
        move_dialog_down(logs_dialog, self.geometry())
        logs_dialog.exec()

    def open_settings_dialog(self) -> None:
        self.settings_dialog = SettingsDialog(self.settings_service)
        move_dialog_down(self.settings_dialog, self.geometry())

        if self.settings_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_settings = self.settings_dialog.get_settings()

        if not new_settings:
            return

        if self.settings_service.radar_max_radius != new_settings.radar_max_radius:
            self.settings_service.radar_max_radius = new_settings.radar_max_radius
            if self.settings_service.radar_radius > new_settings.radar_max_radius:
                self.settings_service.radar_radius = int(new_settings.radar_max_radius)
            self.settings_service.zoom = self.calculate_optimal_zoom(
                new_settings.radar_max_radius
            )
            self.ui.radarRadiusSpinbox.setMaximum(new_settings.radar_max_radius)
            self.refresh_map()

        if self.settings_service.gps_interval_s != new_settings.gps_interval_s:
            self.settings_service.gps_interval_s = new_settings.gps_interval_s
            self.timer_gps.setInterval(new_settings.gps_interval_s * 1000)

        if self.settings_service.main_relays != new_settings.main_relays:
            self.settings_service.main_relays = new_settings.main_relays

    def calculate_optimal_zoom(self, radius_m: float) -> int:
        BASE_RADIUS = 500.0
        BASE_ZOOM = 16
        MAX_TILES_ROW_COUNT = 6

        if radius_m <= 0:
            return BASE_ZOOM

        meter_per_tile = BASE_RADIUS / MAX_TILES_ROW_COUNT
        tiles_count = math.ceil(radius_m / meter_per_tile)
        scale_k = MAX_TILES_ROW_COUNT / tiles_count
        zoom_diff = math.log2(scale_k)

        optimal_zoom = BASE_ZOOM + zoom_diff
        final_zoom = math.floor(optimal_zoom)

        return max(0, min(19, final_zoom))

    def open_range_chart_dialog(self) -> None:
        # TODO: Implement chart dialog
        pass

    # endregion

    # region --- Screen Recording ---

    @pyqtSlot(bool)
    def handle_toggle_recording(self) -> None:
        button = cast(QPushButton, self.sender())

        if button.isChecked():
            filename = f"./screen_records/record_{QDateTime.currentDateTime().toString('yyyy-MM-dd_hh-mm-ss')}.mp4"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            self.recorder.start_recording(filename)
        else:
            self.recorder.stop_recording()

    @pyqtSlot()
    def on_recording_started(self) -> None:
        print("[MainWindow] Recording started. Showing status widget.")
        self.record_status_widget.setVisible(True)

    @pyqtSlot()
    def on_recording_stopped(self) -> None:
        print("[MainWindow] Recording stopped. Hiding status widget.")
        if self.ui.screenRecordButton.isChecked():
            self.ui.screenRecordButton.setChecked(False)
        self.record_status_widget.reset_state()

    @pyqtSlot(str)
    def show_error_message(self, error_text: str) -> None:
        print(f"[MainWindow] Recording Error: {error_text}")
        QMessageBox.critical(self, "Recording Error", error_text)
        self.on_recording_stopped()

    def handle_toggle_recording_pause(self, is_paused: bool) -> None:
        self.recorder.toggle_pause(is_paused)

    # endregion

    # region --- Media Player ---

    def handle_open_file(self) -> None:
        btn = cast(QPushButton, self.sender())

        if not btn.isChecked():
            if hasattr(self, "media_service") and self.media_service:
                self.media_service.stop()
                print("[MainWindow] Media player closed.")
            return

        file_filters = (
            f"{self.tr('Media Files (*.png *.jpg *.jpeg *.bmp *.mp4 *.avi *.mkv)')};;"
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select file to view"),
            "",
            file_filters,
        )

        if not file_path:
            self.ui.filesViewButton.setChecked(False)
            return

        try:
            self.media_service.play(file_path)
        except Exception as e:
            print(
                f"[MainWindow] Critical VLC Error: {e}. Opening in default OS player."
            )
            url = QUrl.fromLocalFile(file_path)
            QDesktopServices.openUrl(url)

    # endregion

    # region --- Modes & Settings ---

    def set_radar_mode(self) -> None:
        if self.is_radar_mode:
            return

        self.is_radar_mode = True
        self.ui.map_background_label.setPixmap(QPixmap())

    def set_map_mode(self) -> None:
        if not self.is_radar_mode:
            return

        self.is_radar_mode = False
        self.scale_map()

    def set_radio_range(self) -> None:
        start_value = self.ui.radioStartDoubleSpinBox.value()
        end_value = self.ui.radioEndDoubleSpinBox.value()

        self.settings_service.radio_range_GHz = [start_value, end_value]
        self.reset_radio_range_status()

        # TODO - Підключити до NetworkService

    def clear_radio_range_values(self) -> None:
        radio_range = self.settings_service.radio_range_GHz

        self.ui.radioStartDoubleSpinBox.setValue(float(radio_range[0]))
        self.ui.radioEndDoubleSpinBox.setValue(float(radio_range[1]))

        self.reset_radio_range_status()

    def reset_radio_range_status(self) -> None:
        self.ui.radioStartDoubleSpinBox.setProperty("status", "saved")
        self.ui.radioEndDoubleSpinBox.setProperty("status", "saved")

        update_element_styles(self.ui.radioStartDoubleSpinBox)
        update_element_styles(self.ui.radioEndDoubleSpinBox)

        self.ui.saveRadioRangePushButton.setEnabled(False)
        update_element_styles(self.ui.saveRadioRangePushButton)
        self.ui.clearRadioRangePushButton.setEnabled(False)
        update_element_styles(self.ui.clearRadioRangePushButton)

    def handle_signal_range_change(self, value: float) -> None:
        current_spin_box = cast(QDoubleSpinBox, self.sender())

        start_spin_box: Optional[QDoubleSpinBox] = None
        end_spin_box: Optional[QDoubleSpinBox] = None

        name = current_spin_box.objectName()
        if name == "radioStartDoubleSpinBox":
            start_spin_box = current_spin_box
            end_spin_box = self.ui.radioEndDoubleSpinBox
        elif name == "radioEndDoubleSpinBox":
            start_spin_box = self.ui.radioStartDoubleSpinBox
            end_spin_box = current_spin_box

        if start_spin_box is None or end_spin_box is None:
            return

        current_spin_box.setProperty("status", "unsaved")
        update_element_styles(current_spin_box)
        self.ui.saveRadioRangePushButton.setEnabled(True)
        update_element_styles(self.ui.saveRadioRangePushButton)
        self.ui.clearRadioRangePushButton.setEnabled(True)
        update_element_styles(self.ui.clearRadioRangePushButton)

        start_spin_box.blockSignals(True)
        end_spin_box.blockSignals(True)

        end_spin_box.setMinimum(start_spin_box.value())
        start_spin_box.setMaximum(end_spin_box.value())

        start_spin_box.blockSignals(False)
        end_spin_box.blockSignals(False)

    def start_jammer(self):
        self.is_jammer_active = True
        self.jammer_start_time = QDateTime.currentDateTime()

        self.set_relays_ui_active(True)

        self.ui.jammerOnTimerButton.setEnabled(False)
        update_element_styles(self.ui.jammerOnTimerButton)
        self.ui.jammerOffTimerButton.setEnabled(True)
        update_element_styles(self.ui.jammerOffTimerButton)

        if self.settings_service.is_jammer_auto_stop_enabled:
            msec = self.settings_service.jammer_auto_stop_interval_s * 1000
            self.jammer_stop_timer.start(msec)
        # TODO - підключити до NetworkService

    def stop_jammer(self):
        self.is_jammer_active = False
        self.jammer_start_time = None

        self.set_relays_ui_active(False)
        self.ui.jammerTimerTime.setText("00:00:00")

        self.ui.jammerOffTimerButton.setEnabled(False)
        update_element_styles(self.ui.jammerOffTimerButton)
        self.ui.jammerOnTimerButton.setEnabled(True)
        update_element_styles(self.ui.jammerOnTimerButton)

        if self.jammer_stop_timer and self.jammer_stop_timer.isActive:
            self.jammer_stop_timer.stop()

        # TODO - підключити до NetworkService

    def set_relays_ui_active(self, state: bool):
        for relay in self.settings_service.main_relays:
            label = getattr(self.ui, f"{relay.lower()}_label", None)
            print("Label", relay, " name:", f"{relay.lower()}_label")
            print(label)
            if label:
                label.setEnabled(state)
                update_element_styles(label)

    # endregion

    # region --- Animations & Updates ---

    def update_time_and_date(self) -> None:
        current_datetime = QDateTime.currentDateTime()
        self.ui.DateLabel.setText(current_datetime.toString("dd.MM.yyyy"))
        self.ui.TimeLabel.setText(current_datetime.toString("hh:mm:ss"))

        if self.is_jammer_active:
            seconds_elapsed = self.jammer_start_time.secsTo(current_datetime)
            jammer_time_display = (
                QTime(0, 0, 0).addSecs(seconds_elapsed).toString("HH:mm:ss")
            )
            self.ui.jammerTimerTime.setText(jammer_time_display)

    def rotate_radar_animation(self) -> None:
        RADAR_ANIMATION_STEP_ANGLE = 6
        current_angle = getattr(self, "radar_angle", 0)
        current_angle = (current_angle + RADAR_ANIMATION_STEP_ANGLE) % 360
        self.radar_angle = current_angle

        base_pixmap = self.draw_radar_section(current_angle)
        self.ui.Radar_Section.setPixmap(base_pixmap)

    def draw_radar_section(self, angle: float) -> QPixmap:
        base_pixmap = QPixmap(self.ui.Radar.size())
        base_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(base_pixmap.width(), base_pixmap.height())
        center = QPointF(base_pixmap.width() / 2, base_pixmap.height() / 2)

        gradient = QConicalGradient(center, -angle)

        if self.detection_manager.has_detections():
            # Red alert colors
            gradient.setColorAt(0.0, QColor(215, 40, 30, 100))
            gradient.setColorAt(0.25, QColor(180, 30, 30, 70))
            gradient.setColorAt(1.0, QColor(100, 30, 30, 20))
        else:
            # Green scanning colors
            gradient.setColorAt(0.0, QColor(40, 215, 30, 90))
            gradient.setColorAt(0.25, QColor(30, 180, 30, 50))
            gradient.setColorAt(1.0, QColor(30, 100, 30, 10))

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, size / 2, size / 2)
        painter.end()

        return base_pixmap

    @asyncSlot()
    async def refresh_map(self) -> None:
        print("[MainWindow] Loading map asynchronously...")
        map_type = self.map_types[self.current_map_type_index]

        result = await self.map_service.get_map_pixmap(
            coord=self.current_coords,
            map_type=map_type,
            add_sizes_k=self.add_sizes_map_k,
        )

        if result:
            pixmap, resolution = result
            print(f"[MainWindow] Map loaded. Res: {resolution:.4f} m/px")

            self.current_map = pixmap
            self.current_map_resolution = resolution

            self.map_center_coords = self.current_coords.copy()

            self.scale_map()
        else:
            QMessageBox.warning(None, self.tr("Error"), self.tr("Failed to load map."))
            print("[MainWindow] Error: Failed to load map.")

    def scale_map(self) -> None:
        if self.is_radar_mode or not self.current_map:
            return

        scale_factor = self._calculate_scale_factor()

        if scale_factor <= 0.0001:
            return

        final_pixmap = self._generate_view_pixmap(scale_factor)

        if final_pixmap and not final_pixmap.isNull():
            self.ui.map_background_label.setPixmap(final_pixmap)
            self.ui.map_background_label.resize(final_pixmap.size())

            self.ui.map_background_label.move(0, 0)

    def _generate_view_pixmap(self, scale_factor: float) -> QPixmap:

        view_w = self.ui.map_background_label.width()
        view_h = self.ui.map_background_label.height()

        if view_w <= 0 or view_h <= 0:
            return QPixmap()

        radar_geo = self.ui.RadarFrame.geometry()

        rx = radar_geo.center().x() - self.ui.map_background_label.x()
        ry = radar_geo.center().y() - self.ui.map_background_label.y()

        orig_w = self.current_map.width()
        orig_h = self.current_map.height()

        gps_cx = orig_w / 2.0
        gps_cy = orig_h / 2.0

        crop_x = gps_cx - (rx / scale_factor)
        crop_y = gps_cy - (ry / scale_factor)

        crop_w = view_w / scale_factor
        crop_h = view_h / scale_factor

        rect_x = int(crop_x)
        rect_y = int(crop_y)
        rect_w = int(math.ceil(crop_w))
        rect_h = int(math.ceil(crop_h))

        cropped = self.current_map.copy(rect_x, rect_y, rect_w, rect_h)

        if cropped.isNull():
            return QPixmap()

        return cropped.scaled(
            view_w,
            view_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _calculate_scale_factor(self) -> float:
        radar_radius_m = self.settings_service.radar_radius
        if radar_radius_m <= 0:
            return 0.0

        radar_view_radius_px = self.ui.RadarFrame.width() / 2.0

        target_px_per_meter = radar_view_radius_px / radar_radius_m

        if self.current_map_resolution <= 0:
            return 0.0
        source_px_per_meter = 1.0 / self.current_map_resolution

        return target_px_per_meter / source_px_per_meter

    @asyncSlot()
    async def change_map_type(self) -> None:
        self.current_map_type_index = (self.current_map_type_index + 1) % len(
            self.map_types
        )
        await self.refresh_map()

    def take_screenshot(self) -> None:
        screenshot = self.grab()
        filename = f"./screenshots/screenshot_{QDateTime.currentDateTime().toString('yyyy-MM-dd_hh-mm-ss')}.png"
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        screenshot.save(filename, "png")
        print(f"[MainWindow] Screenshot saved to: {filename}")

    def update_gps_and_map(self) -> None:
        self.force_gps_update = True
        self.request_gps()

    @pyqtSlot()
    def perform_search(self) -> None:
        text = self.ui.index_search_edit.text().strip()

        if not text:
            self.searched_index = None
            self.update_detection_info()
            self.ui.index_search_edit.setProperty("is_valid", True)
            update_element_styles(self.ui.index_search_edit)
            return

        if not text.isdigit():
            self.ui.index_search_edit.setProperty("is_valid", False)
            update_element_styles(self.ui.index_search_edit)
            return

        target_idx = int(text)
        self.searched_index = target_idx
        self.ui.index_search_edit.setProperty("is_valid", True)
        update_element_styles(self.ui.index_search_edit)

        self.update_detection_info()

    @pyqtSlot(dict)
    def handle_pi_data(self, data: Dict[str, Any]) -> None:
        print(f"[MainWindow] Received generic data from Pi: {data}")

    def update_wifi_signal_info(self) -> None:
        wifi_strength = get_wifi_signal_strength(self.system_service.is_windows)

        wifi_level = 0
        if wifi_strength:
            wifi_level = math.ceil(wifi_strength / (100 / SIGNAL_LEVEL_COUNT))

        self.ui.WiFi_level.setProperty("level", wifi_level)
        update_element_styles(self.ui.WiFi_level)

    def restart_app(self) -> None:
        print("[MainWindow] Logout requested. Restarting application...")
        self.settings_service.remember_me = False
        self.setEnabled(False)
        restart_process()

    # endregion

    def closeEvent(self, event: QCloseEvent) -> None:
        print("[MainWindow] Application closing...")

        if self.recorder.isRunning():
            print("[MainWindow] Closing: Stopping recording thread...")
            self.recorder.stop_recording()

            if not self.recorder.wait(3000):
                print("[MainWindow] Thread did not stop. Forcing termination.")
                self.recorder.terminate()

        event.accept()
