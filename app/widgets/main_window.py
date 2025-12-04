"""
Головне вікно програми (Controller).
Зв'язує графічний інтерфейс (View) з сервісами та логікою. Обробляє навігацію та глобальні події.
"""

import os
import math
import asyncio
import shutil
import subprocess
import keyboard
import re
from PyQt6.QtWidgets import QMainWindow, QApplication, QDialog, QMessageBox, QFileDialog
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
)

from PyQt6 import uic
from qasync import asyncSlot

from app.ui.ui_main_window import Ui_MainWindow
from app.assets import resources_rc

from app.services.api_server import ApiServer
from app.services.map_service import MapService, MapTypes
from app.utils.test_data_provider import TestDataProvider
from app.services.settings_service import SettingsService
from app.protocols import OSService
from app.services.keyboard_service import KeyboardService
from app.widgets.set_map_dialog import SetMapDialog
from app.widgets.autosize_window import make_scalable
from app.services.pi_network_service import PiNetworkService
from app.widgets.record_status_widget import RecordingStatusWidget
from app.services.recording_service import RecordingService
from app.services.media_player_service import MediaPlayerService
from app.utils.ui_utils import update_element_styles
from app.utils.system_utils import (
    get_wifi_signal_strength,
    restart_process,
)


class MainWindow(QMainWindow):
    _sig_start_recording = pyqtSignal(str)
    _sig_stop_recording = pyqtSignal()

    def __init__(
        self,
        settings: SettingsService,
        keyboard: KeyboardService,
        system: OSService,
        parent=None,
    ):
        super().__init__(parent)
        self.settings_service = settings
        self.system_service = system
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
        # Робимо розрахунок при першому показі
        self._update_map_geometry()
        self.refresh_map()

    def changeEvent(self, event):
        # Ловимо подію, яку надіслав installTranslator
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("Зміна мови, оновлюю UI...")
                # Викликаємо авто-згенеровану функцію
                self.ui.retranslateUi(self)
        else:
            # Передаємо всі інші події (натискання клавіш, зміна розміру тощо)
            # на стандартну обробку
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

        # self.api_server = ApiServer(settings=self.settings_service)
        self.pi_network = PiNetworkService(self.settings_service, self)
        self.pi_network.data_received.connect(self.handle_pi_data)

        # self.api_server.on_rf_data = self.handle_rf_data
        # self.api_server.on_audio_alert = self.handle_audio_alert

        self.current_map_type_index = 0
        self.map_types = [e for e in MapTypes]
        self.current_coords = [49.43440, 27.00543]
        self.isRadarMode = False
        self.is_alert = False
        self.translator = QTranslator()

        self.record_status_widget = RecordingStatusWidget(self.settings_service, self)

        self.media_service = MediaPlayerService(self.system_service)
        self.media_service.playback_finished.connect(
            lambda: self.ui.filesViewButton.setChecked(False)
        )

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
        self.ui.homeButton.clicked.connect(self.update_status_bar_with_test_data)
        self.ui.addMapButton.clicked.connect(self.handle_add_map)
        self.ui.screenRecordButton.clicked.connect(self.handle_toggle_recording)
        self.ui.filesViewButton.clicked.connect(self.handle_open_file)

        self.ui.falseAlarmButton.clicked.connect(self.stop_alert)
        self.ui.menuButton.clicked.connect(self.test_draw_dot)
        self.ui.radarButton.clicked.connect(self.set_radar_mode)
        self.ui.mapButton.clicked.connect(self.set_map_mode)
        self.ui.backToLoginButton.clicked.connect(self.restart_app)

        self.ui.saveRadarSettingsBtn.clicked.connect(self.handle_radar_radius_change)

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

        self.test_update_timer = QTimer(self)
        self.test_update_timer.timeout.connect(self.update_status_bar_with_test_data)
        self.test_update_timer.start(10 * 60 * 1000)

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
        # self.api_server.run_server()
        self.listen_for_pi_data()
        self.pi_network.start()

    def _update_map_geometry(self):
        """
        Обчислює та оновлює коефіцієнти та зміщення
        на основі ПОТОЧНИХ розмірів віджетів.
        (з розширеним логуванням)
        """

        # Перевірка, чи віджети вже завантажені
        if not self.ui.Radar.width() or not self.ui.Radar.height():
            return

        # --- 1. Збір вхідних даних ---
        radar_width = self.ui.RadarFrame.width()
        radar_height = self.ui.RadarFrame.height()

        map_bg_width = self.ui.map_background_label.width()
        map_bg_height = self.ui.map_background_label.height()

        # --- 2. Розрахунок коефіцієнтів ---
        self.add_sizes_map_k = [
            map_bg_width / radar_width,
            map_bg_height / radar_height,
        ]

    def load_language(self):
        # Видаляємо старий перекладач
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

    def handle_rf_data(self, analyzed_results):
        print(f"Слот отримав проаналізовані RF дані: {analyzed_results}")
        self.flush_radar_dots()
        if analyzed_results:
            if "0" in analyzed_results:
                self.create_radar_dot(180, 350)
            if "1" in analyzed_results:
                self.create_radar_dot(240, 150)

    def handle_audio_alert(self, status):
        print(f"Слот отримав звукову тривогу: {status}")
        self.ui.Sound_alert.setProperty("alert", status)

    def handle_radar_radius_change(self):
        new_radar_radius = self.ui.radarRadiusSpinbox.value()
        self.settings_service.radar_radius = new_radar_radius
        self.scale_map()

        config_data = {"msg_type": "config", "radar_radius": new_radar_radius}
        self.pi_network.send_data(config_data)

    def handle_add_map(self):
        btn = self.sender()

        if btn.isChecked() == False:
            self.refresh_map()
            return

        self.open_set_map_dialog()

    def open_set_map_dialog(self):

        # 1. Створюємо екземпляр діалогу
        self.dialog = SetMapDialog(
            settings=self.settings_service, add_sizes_map_k=self.add_sizes_map_k
        )

        ScalableDialog = make_scalable(QDialog)
        self.scalable_dialog = ScalableDialog(widget_to_scale=self.dialog)

        # 3. Використовуємо .exec() для блокуючого виклику
        result = self.scalable_dialog.exec()

        # 4. Перевіряємо результат
        if result == QDialog.DialogCode.Accepted:

            # 5. Отримуємо дані
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

            # Напряму викликаємо метод-слот
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

        if not btn.isChecked():
            if hasattr(self, "media_service") and self.media_service:
                self.media_service.stop()
                print("Переглядач успішно закритий")
            return

        file_filters = (
            f"{self.tr('Медіа файли (*.png *.jpg *.jpeg *.bmp *.mp4 *.avi *.mkv)')};;"
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

        try:
            self.media_service.play(file_path)
        except Exception as e:
            print(f"Критична помилка запуску VLC: {e}")
            url = QUrl.fromLocalFile(file_path)
            QDesktopServices.openUrl(url)

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

        # Малюємо градієнтний промінь
        gradient = QConicalGradient(center, -angle)

        if self.is_alert:
            gradient.setColorAt(0.0, QColor(215, 40, 30, 100))
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

    def create_radar_dot(self, angle, distance):
        pixmap = self.ui.Radar.pixmap()
        self.radar_background = self.ui.Radar.pixmap()
        if not pixmap or pixmap.isNull():
            return

        painter = QPainter(pixmap)
        pen = QPen(QColor("red"), 20)
        painter.setPen(pen)

        center_x = pixmap.width() / 2
        center_y = pixmap.height() / 2
        rad_angle = math.radians(angle - 90)

        x = center_x + distance * math.cos(rad_angle)
        y = center_y + distance * math.sin(rad_angle)

        painter.drawPoint(int(x), int(y))
        painter.end()
        self.ui.Radar.setPixmap(pixmap)

    def clear_radar_dots(self):
        """Видаляє намальовані точки з радара, відновлюючи фон."""
        if not hasattr(self, "radar_background"):
            # Зберігання фону
            return

        clean_pixmap = self.radar_background.copy()
        self.ui.Radar.setPixmap(clean_pixmap)

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
            radar_radius_m = self.settings_service.radar_radius  # у метрах
            radar_max_radius_m = self.settings_service.radar_max_radius  # у метрах
            radius_px = self.ui.RadarFrame.width() / 2  # піксельний розмір радара

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

            # === Центрування карти ===
            self.ui.map_background_label.setPixmap(scaled_pixmap)
            self.ui.map_background_label.resize(scaled_pixmap.size())

            # Отримуємо центр радара
            radar_center = self.ui.RadarFrame.geometry().center()

            # Отримуємо центр зображення
            pixmap_center = self.ui.map_background_label.rect().center()

            # Розраховуємо нову позицію для QLabel, щоб центри співпали
            new_x = radar_center.x() - pixmap_center.x()
            new_y = radar_center.y() - pixmap_center.y()

            # Переміщуємо фон карти
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
    async def update_status_bar_with_test_data(self):

        data = self.test_data_provider.get_next_test_data()
        # self.ghz24_1.setProperty("band_active", data["ghz24_1"])
        # self.ghz58_1.setProperty("band_active", data["ghz58_1"])
        self.ui.RF_alert.setProperty("alert", data["rf_alert"])
        self.ui.Sound_alert.setProperty("alert", data["sound_alert"])
        self.current_coords = data["coord"]
        print(f"Оновлено тестові дані. Координати: {self.current_coords}")

        await self.refresh_map()

    def test_draw_dot(self):
        if self.is_alert == True:
            self.stop_alert()
            return

        self.start_alert()

    def start_alert(self):
        self.create_radar_dot(45, 200)
        self.is_alert = True
        self.ui.falseAlarmButton.setEnabled(True)

    def stop_alert(self):
        self.clear_radar_dots()
        self.is_alert = False
        self.ui.falseAlarmButton.setEnabled(False)

    @pyqtSlot(dict)
    def handle_pi_data(self, data):
        """Обробка даних, отриманих від іншої Raspberry Pi."""
        # print(f"Отримано дані від Pi: {data}")

        # Приклад: якщо прийшли координати або статус тривоги
        if "rf_alert" in data:
            if data["rf_alert"]:
                self.start_alert()
            else:
                self.stop_alert()

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
            self.recorder.stop_recording()  # Кажемо потоку зупинитися

            # Чекаємо до 3 секунд, поки він зупиниться
            if not self.recorder.wait(3000):
                print("[MainWindow] Потік не відповів. Примусова зупинка.")
                self.recorder.terminate()  # Аварійний варіант

        event.accept()
