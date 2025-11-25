"""
Головне вікно програми (Controller).
Зв'язує графічний інтерфейс (View) з сервісами та логікою. Обробляє навігацію та глобальні події.
"""

import os
import math
import asyncio
from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QDialog,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import (
    QTimer,
    QDateTime,
    Qt,
    QPointF,
    QEvent,
    QCoreApplication,
    QTranslator,
    pyqtSlot,
    pyqtSignal,
    QThread,
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
    QTextCursor,
)

from PyQt6 import uic
from qasync import asyncSlot

from app.ui.ui_main_window import Ui_MainWindow
from app.assets import resources_rc

from app.services.api_server import ApiServer
from app.services.map_service import MapService, MapTypes
from app.utils.test_data_provider import TestDataProvider
from app.services.settings_service import SettingsService

# from app.services.keyboard_service import KeyboardService
from app.widgets.set_map_dialog import SetMapDialog
from app.widgets.autosize_window import make_scalable
from app.widgets.record_status_widget import RecordingStatusWidget
from app.services.settings_service import SettingsService
from app.services.map_service import MapService, MapTypes
from app.services.keyboard_service import KeyboardService
from app.services.recording_service import RecordingService
from app.services.media_player_service import MediaPlayerService
from app.services.pi_network_service import PiNetworkService
from app.core.detection_manager import DetectionManager
from app.models.detection_event import DetectionEvent
from app.protocols import OSService
from app.utils.ui_utils import update_element_styles
from app.utils.test_data_provider import TestDataProvider
from app.utils.system_utils import (
    get_wifi_signal_strength,
    restart_process,
)


class MainWindow(QMainWindow):
    _sig_start_recording = pyqtSignal(str)
    _sig_stop_recording = pyqtSignal()

    def __init__(self, settings: SettingsService, keyboard, parent=None):
        super().__init__(parent)
        self.settings_service = settings
        self.keyboard_service = keyboard

        self._load_ui()
        print("[MainWindow] Інтерфейс завантажено.")

        self._setup_state_variables()
        self._init_recording_service()

        self._adjust_fields()

        self._connect_handlers()
        self._setup_timers()

        self.update_wifi_signal_info()

        self.change_language()

        self._start_async_tasks()

        print("Головне вікно успішно ініціалізовано.")

    def showEvent(self, event):
        """
        Викликається, коли віджет показується.
        Використовуємо для первинного розрахунку геометрії.
        """
        super().showEvent(event)
        self.ui.map_background_label.setScaledContents(False)

        self._update_map_geometry()
        self.refresh_map()

        self.radar_clean_pixmap = QPixmap(":/images/radar.png").scaled(
            self.ui.Radar.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("Зміна мови, оновлюю UI...")
                self.ui.retranslateUi(self)
        else:

            super().changeEvent(event)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/main_window.ui", self)
            self.ui = self

    def _setup_state_variables(self):

        self.test_data_provider = TestDataProvider()

        self.map_service = MapService(settings=self.settings_service)

        self.searched_index = None

        self.api_server.on_rf_data = self.handle_rf_data
        self.api_server.on_audio_alert = self.handle_audio_alert

        self.current_map_type_index = 0
        self.map_types = [e for e in MapTypes]
        self.current_coords = [49.43440, 27.00543]
        self.isRadarMode = False
        self.is_alert = False
        self.translator = QTranslator()

        self.record_status_widget = RecordingStatusWidget(self.settings_service, self)

        self.media_process = None

    def _init_recording_service(self):
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

    def _adjust_fields(self):
        radar_max_radius = self.settings_service.radar_max_radius
        self.ui.radarRadiusSpinbox.setMaximum(radar_max_radius)

        radar_radius = self.settings_service.radar_radius
        self.ui.radarRadiusSpinbox.setValue(radar_radius)

        radio_range = self.settings_service.radio_range_GHz

        self.ui.radioStartDoubleSpinBox.setValue(float(radio_range[0]))
        self.ui.radioEndDoubleSpinBox.setValue(float(radio_range[1]))

        sound_range = self.settings_service.sound_range_GHz
        self.ui.soundStartDoubleSpinBox.setValue(float(sound_range[0]))
        self.ui.soundEndDoubleSpinBox.setValue(float(sound_range[1]))

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

    def _connect_handlers(self):
        self.ui.mapLayoutButton.clicked.connect(self.change_map_type)
        self.ui.screenSaveButton.clicked.connect(self.take_screenshot)
        self.ui.homeButton.clicked.connect(self.update_gps_and_map)
        self.ui.addMapButton.clicked.connect(self.handle_add_map)
        self.ui.screenRecordButton.clicked.connect(self.handle_toggle_recording)
        self.ui.filesViewButton.clicked.connect(self.handle_open_file)

        self.ui.falseAlarmButton.clicked.connect(self.handle_false_alarm)
        # self.ui.menuButton.clicked.connect(self.test_draw_dot)
        self.ui.radarButton.clicked.connect(self.set_radar_mode)
        self.ui.mapButton.clicked.connect(self.set_map_mode)
        self.ui.backToLoginButton.clicked.connect(self.restart_app)

        self.ui.saveRadarSettingsBtn.clicked.connect(self.handle_radar_radius_change)
        self.ui.index_search_edit.returnPressed.connect(self.perform_search)

        self.ui.saveRadioRangePushButton.clicked.connect(self.set_radio_range)
        self.ui.saveSoundRangePushButton.clicked.connect(self.set_sound_range)
        self.ui.clearRadioRangePushButton.clicked.connect(self.clear_radio_range_values)
        self.ui.clearSoundRangePushButton.clicked.connect(self.clear_sound_range_values)

        self.ui.radioStartDoubleSpinBox.valueChanged.connect(
            self.handle_signal_range_change
        )
        self.ui.radioEndDoubleSpinBox.valueChanged.connect(
            self.handle_signal_range_change
        )
        self.ui.soundStartDoubleSpinBox.valueChanged.connect(
            self.handle_signal_range_change
        )
        self.ui.soundEndDoubleSpinBox.valueChanged.connect(
            self.handle_signal_range_change
        )

        self.ui.langComboBox.currentIndexChanged.connect(self.change_language)

        self.record_status_widget.ui.pause_button.toggled.connect(
            self.handle_toggle_recording_pause
        )

    def _setup_timers(self):
        self.timer_1sec = QTimer(self)
        self.timer_1sec.timeout.connect(self.update_time_and_date)
        self.timer_1sec.start(1000)

        self.timer_radar = QTimer(self)
        self.timer_radar.timeout.connect(self.rotate_radar_animation)
        self.timer_radar.start(60)

        # self.test_update_timer = QTimer(self)
        # self.test_update_timer.timeout.connect(self.update_status_bar_with_test_data)
        # self.test_update_timer.start(10 * 60 * 1000)

        self.timer_wifi = QTimer(self)
        self.timer_wifi.timeout.connect(self.update_wifi_signal_info)
        self.timer_wifi.start(30 * 1000)

    @asyncSlot()
    async def _start_async_tasks(self):
        """
        Запускає всі фонові асинхронні задачі.
        Цей метод має викликатися з 'main' ПІСЛЯ створення вікна.
        """
        print("Запуск фонових асинхронних задач (сервер та слухач)...")
        self.pi_network.start()

    def _update_map_geometry(self):
        """
        Обчислює та оновлює коефіцієнти та зміщення
        на основі ПОТОЧНИХ розмірів віджетів.
        (з розширеним логуванням)
        """

        if not self.ui.Radar.width() or not self.ui.Radar.height():
            return

        radar_width = self.ui.RadarFrame.width()
        radar_height = self.ui.RadarFrame.height()

        map_bg_width = self.ui.map_background_label.width()
        map_bg_height = self.ui.map_background_label.height()

        self.add_sizes_map_k = [
            map_bg_width / radar_width,
            map_bg_height / radar_height,
        ]

    def load_language(self):
        lang_code = self.settings_service.lang_code

        if lang_code == None:
            return

        QCoreApplication.removeTranslator(self.translator)

        # Завантажуємо та встановлюємо новий
        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    def change_language(self):
        index = self.ui.langComboBox.currentIndex()
        new_lang_code = None

        if index == 1:
            new_lang_code = "en"
        else:
            new_lang_code = "uk"

        self.settings_service.lang_code = new_lang_code
        print("Ok")
        if self.settings_service.compiled_ui_using_enabled:
            self.load_language()

    @asyncSlot()
    async def listen_for_pi_data(self):
        """Асинхронно слухає та обробляє дані з Raspberry Pi."""
        # Тут буде ваша логіка для постійного отримання даних
        # Наприклад, через веб-сокет або HTTP-запити
        print("Запущено асинхронний слухач даних...")
        while True:
            # `await asyncio.sleep(1)` імітує асинхронне очікування.
            await asyncio.sleep(1)
            # self.handle_rf_data(data) # Викликаємо обробник, коли дані прийшли

    def handle_sound_data(self, data):
        """Заглушка для обробки потокових звукових даних."""
        pass  # Логіка буде додана пізніше

    @pyqtSlot()
    def _update_detection_ui(self):
        """Оновлює UI на основі поточних детекцій."""
        self.update_radar()
        self.update_detection_info()
        self.update_alert_status()

    def update_radar(self):
        """Перемальовує радар. Точки поза радіусом 'липнуть' до краю."""
        detections, indices = self.detection_manager.get_detections()

        POINT_SIZE = 20

        pixmap = self.radar_clean_pixmap.copy()
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)

        center_x = pixmap.width() / 2
        center_y = pixmap.height() / 2

        offset_x = 0
        offset_y = -15

        max_px_radius = min(center_x, center_y)

        max_meters_setting = self.settings_service.radar_radius
        if max_meters_setting <= 0:
            max_meters_setting = 1000

        scale = max_px_radius / max_meters_setting

        for event_id, event in detections.items():
            index = indices.get(event_id, "?")

            pixel_dist = event.distance * scale

            is_out_of_bounds = pixel_dist > max_px_radius
            is_on_border = pixel_dist >= max_px_radius - POINT_SIZE / 2

            if is_out_of_bounds or is_on_border:
                pixel_dist = max_px_radius - 15
                if event.angle > 320 or event.angle < 40:
                    offset_y = 0
                    offset_x = 15

            if is_out_of_bounds:
                painter.setPen(QPen(QColor("orange"), POINT_SIZE - 2))
            else:
                color = QColor("red")
                painter.setPen(QPen(color, POINT_SIZE))

            rad_angle = math.radians(event.angle - 90)

            x = center_x + pixel_dist * math.cos(rad_angle)
            y = center_y + pixel_dist * math.sin(rad_angle)

            painter.drawPoint(int(x), int(y))

            painter.setPen(QPen(QColor("black"), 1))
            painter.drawText(int(x) + offset_x, int(y) + offset_y, str(index))

        painter.end()
        self.ui.Radar.setPixmap(pixmap)

    def update_detection_info(self):
        """
        Відображає детальну інформацію ТІЛЬКИ для self.searched_index.
        Якщо нічого не шукаємо -> пусто.
        Якщо ціль з таким індексом зникла -> "Target Lost".
        """
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
                "Ціль зникла з радару або ще не виявлена."
            )

    def find_event_by_searched_index(self):
        detections, indices = self.detection_manager.get_detections()

        target_event = None
        for eid, idx in indices.items():
            if idx == self.searched_index:
                target_event = detections.get(eid)
                break

        return target_event

    def update_alert_status(self):
        """Оновлює статус тривог на основі детекцій."""
        detections, _ = self.detection_manager.get_detections()

        has_rf = any(e.type == "RF" for e in detections.values())
        has_sound = any(e.type == "Sound" for e in detections.values())

        self.ui.RF_alert.setProperty("alert", has_rf)
        self.ui.Sound_alert.setProperty("alert", has_sound)
        update_element_styles(self.ui.RF_alert)
        update_element_styles(self.ui.Sound_alert)

        self.ui.falseAlarmButton.setEnabled(self.detection_manager.has_detections())

    def handle_false_alarm(self):
        """Повідомляє про хибну тривогу для поточної детекцій і очищує."""
        target_event = self.find_event_by_searched_index()
        if target_event:
            self.pi_network.report_false_alarm(target_event.id)
            self.detection_manager.remove_detection(target_event.id)

    def request_gps(self):
        """Запитує GPS з callback для обробки відповіді."""
        self.pi_network.request_remote_gps()

    def update_gps_ui(self, data):
        strength = data.get("gps_strength")
        lat = data.get("gps_lat")
        lon = data.get("gps_lon")

        if self.current_coords[0] != lat or self.current_coords[1] != lon:
            self.current_coords = [lat, lon]
            self.refresh_map()

        print("gps_signal_strength:", strength)

        gps_level = 0

        if strength:
            gps_level = math.ceil(strength / 25)

        self.ui.GPS_level.setProperty("level", gps_level)
        update_element_styles(self.ui.GPS_level)

    @pyqtSlot(dict)
    def handle_gps(self, data):
        """Обробка GPS-відповіді з викликом."""
        self.update_gps_ui(data)

        print(
            f"[MainWindow] Отримано GPS: {data.get('gps_lat')}, {data.get('gps_lon')}"
        )

    def handle_radar_radius_change(self):
        new_radar_radius = self.ui.radarRadiusSpinbox.value()
        self.settings_service.radar_radius = new_radar_radius

        self.scale_map()

        self.update_radar()

    def handle_add_map(self):
        btn = self.sender()

        if btn.isChecked() == False:
            self.refresh_map()
            return

        self.open_set_map_dialog()

    def open_set_map_dialog(self):

        self.dialog = SetMapDialog(
            settings=self.settings_service, add_sizes_map_k=self.add_sizes_map_k
        )

        ScalableDialog = make_scalable(QDialog)
        self.scalable_dialog = ScalableDialog(widget_to_scale=self.dialog)

        result = self.scalable_dialog.exec()

        if result == QDialog.DialogCode.Accepted:

            settings_data = self.scalable_dialog.get_settings()

            if self.current_map:
                self.current_map = settings_data["pixmap"]
                print("Width:", self.current_map.width())
                radar_max_radius = self.settings_service.radar_max_radius
                self.current_map_radius = (
                    settings_data["px_per_meter"] * radar_max_radius
                )
                self.scale_map()

            print("ГОЛОВНЕ ВІКНО: Отримано налаштування!")

        else:
            self.ui.addMapButton.setChecked(False)
            print("ГОЛОВНЕ ВІКНО: Налаштування скасовано.")

        self.scalable_dialog = None

    @pyqtSlot(bool)
    def handle_toggle_recording(self):
        button = self.sender()

        if button.isChecked():
            filename = f"./screen_records/record_{QDateTime.currentDateTime().toString('yyyy-MM-dd_hh-mm-ss')}.mp4"
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            self.recorder.start_recording(filename)
        else:
            self.recorder.stop_recording()

    @pyqtSlot()
    def on_recording_started(self):
        print("[MainWindow] Отримано підтвердження старту. Показ віджета.")
        self.record_status_widget.setVisible(True)

    @pyqtSlot()
    def on_recording_stopped(self):
        print("[MainWindow] Отримано підтвердження зупинки. Ховаємо віджет.")
        if self.ui.screenRecordButton.isChecked():
            self.ui.screenRecordButton.setChecked(False)
        self.record_status_widget.reset_state()

    @pyqtSlot(str)
    def show_error_message(self, error_text):
        print(f"ПОМИЛКА ЗАПИСУ: {error_text}")
        QMessageBox.critical(self, "Помилка запису", error_text)
        self.on_recording_stopped()

    def handle_toggle_recording_pause(self, is_paused):
        self.recorder.toggle_pause(is_paused)

    def handle_open_file(self):
        btn = self.sender()

        if btn.isChecked() == False:
            if self.media_process:
                self.media_process.close()
                print("Переглядач успішно закритий")
            return

        file_filters = (
            f"{self.tr('Медіа файли (*.png *.jpg *.jpeg *.bmp *.mp4 *.avi *.mkv)')};;"
            # f"{self.tr('Всі файли (*.*)')}"
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Оберіть файл для перегляду"),
            "",
            file_filters,
        )

        if not file_path:
            self.ui.filesViewButton.setChecked(False)
            return

        program_path = self.get_vlc_executable()

        url = QUrl.fromLocalFile(file_path)

        if not program_path:
            print("VLC не знайдено. Відкриваємо у дефолтній програмі...")
            QDesktopServices.openUrl(url)
            return

        arguments = [
            "--fullscreen",
            "--play-and-pause",
            "--image-duration=-1",
            # "--no-qt-privacy-ask",  # Щоб не спливали діалоги
            # "--no-qt-error-dialogs",  # Не показувати помилки
            "--global-key-quit=q",  # Закривається на q
            "--loop",
            url.toString(),
        ]

        try:
            self.media_process = QProcess(self)
            self.media_process.finished.connect(
                lambda *_: self.ui.filesViewButton.setChecked(False)
            )

            self.media_process.start(program_path, arguments)
        except Exception as e:
            print(f"Критична помилка запуску VLC: {e}")
            url = QUrl.fromLocalFile(file_path)
            QDesktopServices.openUrl(url)

    def get_vlc_executable(self):
        """
        Знаходить шлях до виконуваного файлу VLC в залежності від ОС.
        """
        system = platform.system()

        if system == "Windows":
            # Шукаємо у стандартних папках Windows
            possible_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path

            # Якщо не знайшли, шукаємо в системному PATH
            path_in_env = shutil.which("vlc")
            if path_in_env:
                return path_in_env

        elif system == "Linux" or system == "Darwin":
            path_in_env = shutil.which("vlc")
            if path_in_env:
                return path_in_env

        # Якщо нічого не знайшли
        return None

    def set_radar_mode(self):
        if self.isRadarMode:
            return

        self.isRadarMode = True
        self.ui.map_background_label.setPixmap(QPixmap())

    def set_map_mode(self):
        if self.isRadarMode == False:
            return

        self.isRadarMode = False
        self.scale_map()

    def set_radio_range(self):
        start_value = self.ui.radioStartDoubleSpinBox.value()
        end_value = self.ui.radioEndDoubleSpinBox.value()

        self.settings_service.radio_range_GHz = [start_value, end_value]
        self.reset_radio_range_status()

    def clear_radio_range_values(self):
        radio_range = self.settings_service.radio_range_GHz

        self.ui.radioStartDoubleSpinBox.setValue(float(radio_range[0]))
        self.ui.radioEndDoubleSpinBox.setValue(float(radio_range[1]))

        self.reset_radio_range_status()

    def reset_radio_range_status(self):
        self.ui.radioStartDoubleSpinBox.setProperty("status", "saved")
        self.ui.radioEndDoubleSpinBox.setProperty("status", "saved")

        update_element_styles(self.ui.radioStartDoubleSpinBox)
        update_element_styles(self.ui.radioEndDoubleSpinBox)

    def set_sound_range(self):
        start_value = self.ui.soundStartDoubleSpinBox.value()
        end_value = self.ui.soundEndDoubleSpinBox.value()

        self.settings_service.sound_range_GHz = [start_value, end_value]

        self.reset_sound_range_status()

    def clear_sound_range_values(self):
        sound_range = self.settings_service.sound_range_GHz

        self.ui.soundStartDoubleSpinBox.setValue(float(sound_range[0]))
        self.ui.soundEndDoubleSpinBox.setValue(float(sound_range[1]))

        self.reset_sound_range_status()

    def reset_sound_range_status(self):
        self.ui.soundStartDoubleSpinBox.setProperty("status", "saved")
        self.ui.soundEndDoubleSpinBox.setProperty("status", "saved")

        update_element_styles(self.ui.soundStartDoubleSpinBox)
        update_element_styles(self.ui.soundEndDoubleSpinBox)

    def handle_signal_range_change(self, value):
        current_spin_box = self.sender()

        start_spin_box = None
        end_spin_box = None

        match current_spin_box.objectName():
            case "radioStartDoubleSpinBox":
                start_spin_box = current_spin_box
                end_spin_box = self.ui.radioEndDoubleSpinBox
            case "radioEndDoubleSpinBox":
                start_spin_box = self.ui.radioStartDoubleSpinBox
                end_spin_box = current_spin_box
            case "soundStartDoubleSpinBox":
                start_spin_box = current_spin_box
                end_spin_box = self.ui.soundEndDoubleSpinBox
            case "soundEndDoubleSpinBox":
                start_spin_box = self.ui.soundStartDoubleSpinBox
                end_spin_box = current_spin_box

        if start_spin_box is None or end_spin_box is None:
            return

        current_spin_box.setProperty("status", "unsaved")

        update_element_styles(current_spin_box)

        start_spin_box.blockSignals(True)
        end_spin_box.blockSignals(True)

        end_spin_box.setMinimum(start_spin_box.value())
        start_spin_box.setMaximum(end_spin_box.value())

        start_spin_box.blockSignals(False)
        end_spin_box.blockSignals(False)

    def update_time_and_date(self):
        current_datetime = QDateTime.currentDateTime()
        self.ui.DateLabel.setText(current_datetime.toString("dd.MM.yyyy"))
        self.ui.TimeLabel.setText(current_datetime.toString("hh:mm:ss"))

    def rotate_radar_animation(self):
        current_angle = getattr(self, "radar_angle", 0)
        current_angle = (current_angle + 6) % 360
        self.radar_angle = current_angle

        base_pixmap = self.draw_radar_section(current_angle)

        self.ui.Radar_Section.setPixmap(base_pixmap)

    def draw_radar_section(self, angle):
        base_pixmap = QPixmap(self.ui.Radar.size())
        base_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(base_pixmap.width(), base_pixmap.height())
        center = QPointF(base_pixmap.width() / 2, base_pixmap.height() / 2)

        gradient = QConicalGradient(center, -angle)

        if self.detection_manager.has_detections():
            gradient.setColorAt(
                0.0, QColor(215, 40, 30, 100)
            )  # яскраво-червоний на початку
            gradient.setColorAt(0.25, QColor(180, 30, 30, 70))
            gradient.setColorAt(1.0, QColor(100, 30, 30, 20))
        else:
            gradient.setColorAt(0.0, QColor(40, 215, 30, 90))
            gradient.setColorAt(0.25, QColor(30, 180, 30, 50))
            gradient.setColorAt(1.0, QColor(30, 100, 30, 10))

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, size / 2, size / 2)
        painter.end()

        return base_pixmap

    def flush_radar_dots(self):
        self.ui.Radar.setPixmap(QPixmap(":/images/radar.png"))

    @asyncSlot()
    async def refresh_map(self):
        print("Запускаю асинхронне завантаження карти...")
        map_type = self.map_types[self.current_map_type_index]

        pixmap, current_radius_px = await self.map_service.get_map_pixmap(
            coord=self.current_coords,
            map_type=map_type,
            add_sizes_k=self.add_sizes_map_k,
        )

        if pixmap:
            print("Карта успішно завантажена.")
            self.current_map = pixmap
            self.current_map_radius = current_radius_px

            self.scale_map()

        else:
            QMessageBox.warning(
                None, self.tr("Помилка"), self.tr("Не вдалося завантажити карту.")
            )
            print("Не вдалося завантажити карту.")

    def scale_map(self):

        if self.isRadarMode:
            print("Режим радару: зміна карти не відбувається")
            return

        pixmap = self.current_map
        current_radius_px = self.current_map_radius
        if pixmap:
            radar_radius_m = self.settings_service.radar_radius
            radar_max_radius_m = self.settings_service.radar_max_radius
            radius_px = self.ui.RadarFrame.width() / 2

            scale_factor = (radius_px / current_radius_px) * (
                radar_max_radius_m / radar_radius_m
            )
            print(f"Масштабування карти: {scale_factor:.3f}x")

            scaled_pixmap = pixmap.scaled(
                int(pixmap.width() * scale_factor),
                int(pixmap.height() * scale_factor),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.ui.map_background_label.setPixmap(scaled_pixmap)
            self.ui.map_background_label.resize(scaled_pixmap.size())

            radar_center = self.ui.RadarFrame.geometry().center()

            pixmap_center = self.ui.map_background_label.rect().center()

            new_x = radar_center.x() - pixmap_center.x()
            new_y = radar_center.y() - pixmap_center.y()

            self.ui.map_background_label.move(new_x, new_y)
        else:
            print("При зміні радіусу карта не буда знайдена.")

    @asyncSlot()
    async def change_map_type(self):
        self.current_map_type_index = (self.current_map_type_index + 1) % len(
            self.map_types
        )
        await self.refresh_map()

    def take_screenshot(self):
        screenshot = self.grab()
        filename = f"./screenshots/screenshot_{QDateTime.currentDateTime().toString('yyyy-MM-dd_hh-mm-ss')}.png"
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        screenshot.save(filename, "png")
        print(f"Знімок екрану збережено як {filename}")

    @asyncSlot()
    async def update_gps_and_map(self):
        self.request_gps()

        await self.refresh_map()

    @pyqtSlot()
    def perform_search(self):
        """
        Встановлює активний індекс для відображення інформації.
        Викликається при натисканні Enter у полі пошуку.
        """
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
    def handle_pi_data(self, data):
        """Обробка загальних даних від іншої Raspberry Pi."""
        print(f"Отримано загальні дані від Pi: {data}")

    def update_wifi_signal_info(self):
        wifi_strength = get_wifi_signal_strength(self.system_service.is_windows)
        print("wifi_signal_strength:", wifi_strength)

        wifi_level = 0

        if wifi_strength:
            wifi_level = math.ceil(wifi_strength / 25)

        self.ui.WiFi_level.setProperty("level", wifi_level)
        update_element_styles(self.ui.WiFi_level)

    def restart_app(self):
        self.settings_service.remember_me = False
        self.setEnabled(False)
        print("Performing restart...")

        QTimer.singleShot(8000, restart_process)

    def closeEvent(self, event):
        print("Закриття програми...")

        if self.recorder.isRunning():
            print("[MainWindow] Закриття. Зупиняю потік запису...")
            self.recorder.stop_recording()

            if not self.recorder.wait(3000):
                print("[MainWindow] Потік не відповів. Примусова зупинка.")
                self.recorder.terminate()

        event.accept()
