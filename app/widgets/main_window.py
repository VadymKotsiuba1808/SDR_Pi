import math
import asyncio
import platform
import subprocess
import re
from PyQt6.QtWidgets import QMainWindow, QApplication, QDialog
from PyQt6.QtCore import (
    QTimer,
    QDateTime,
    Qt,
    QPointF,
    QEvent,
    QCoreApplication,
    QTranslator,
)
from PyQt6.QtGui import QPixmap, QConicalGradient, QPainter, QColor, QPen

# from PyQt6 import uic
from qasync import asyncSlot

from app.ui.ui_main_window import Ui_MainWindow
from app.assets import resources_rc

from app.services.api_server import ApiServer
from app.services.map_service import MapService, MapTypes
from app.utils.test_data_provider import TestDataProvider
from app.services.settings_service import SettingsService
from app.widgets.set_map_dialog import SetMapDialog
from app.widgets.autosize_window import make_scalable


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings

        # uic.loadUi("app/ui/main_window.ui", self)
        self.ui = Ui_MainWindow()  # Створюємо екземпляр UI
        self.ui.setupUi(self)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.test_data_provider = TestDataProvider()

        self.map_service = MapService(settings=self.settings_service)

        self.api_server = ApiServer(settings=self.settings_service)

        # 2. Передаємо йому методи з MainWindow як callback-функції
        self.api_server.on_rf_data = self.handle_rf_data
        self.api_server.on_audio_alert = self.handle_audio_alert

        self._setup_timers()
        self._setup_state_variables()

        self._adjust_fields()
        self._connect_handlers()

        self.update_wifi_signal_info()

        self.ui.Radar_Red.hide()

        self.load_language()

        self.start_async_tasks()

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
            print("Зміна мови, оновлюю UI...")
            # Викликаємо авто-згенеровану функцію
            self.ui.retranslateUi(self)
        else:
            # Передаємо всі інші події (натискання клавіш, зміна розміру тощо)
            # на стандартну обробку
            super().changeEvent(event)

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

    def _connect_handlers(self):
        self.ui.mapLayoutButton.clicked.connect(self.change_map_type)
        self.ui.screenSaveButton.clicked.connect(self.take_screenshot)
        self.ui.homeButton.clicked.connect(self.update_status_bar_with_test_data)
        self.ui.addMapButton.clicked.connect(self.open_set_map_dialog)

        self.ui.menuButton.clicked.connect(self.test_draw_dot)
        self.ui.radarButton.clicked.connect(self.set_radar_mode)
        self.ui.mapButton.clicked.connect(self.set_map_mode)

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
        self.timer_wifi.start(2 * 60 * 1000)

    def _setup_state_variables(self):
        self.current_map_type_index = 0
        self.map_types = [e for e in MapTypes]
        self.current_coords = [49.43440, 27.00543]
        self.isRadarMode = False
        self.is_warning = False
        self.translator = QTranslator()

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
        path = f"app/i18n/qm/app_{lang_code}.qm"  # Перевірте правильність шляху
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    @asyncSlot()
    async def start_async_tasks(self):
        """
        Запускає всі фонові асинхронні задачі.
        Цей метод має викликатися з 'main' ПІСЛЯ створення вікна.
        """
        print("Запуск фонових асинхронних задач (сервер та слухач)...")
        self.api_server.run_server()
        self.listen_for_pi_data()

    @asyncSlot()
    async def listen_for_pi_data(self):
        """Асинхронно слухає та обробляє дані з Raspberry Pi."""
        # Тут буде ваша логіка для постійного отримання даних
        # Наприклад, через веб-сокет або HTTP-запити
        print("Запущено асинхронний слухач даних...")
        while True:
            # `await asyncio.sleep(1)` імітує асинхронне очікування.
            # Замініть це на ваш реальний код очікування даних.
            # наприклад: data = await get_data_from_pi()
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
            # Якщо користувач натиснув "Зберегти" і валідація пройшла:

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
            # Якщо користувач натиснув "Скасувати" або закрив вікно
            print("ГОЛОВНЕ ВІКНО: Налаштування скасовано.")

        # 6. Очищуємо посилання
        self.scalable_dialog = None

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

        self.update_element_styles(self.ui.radioStartDoubleSpinBox)
        self.update_element_styles(self.ui.radioEndDoubleSpinBox)

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

        self.update_element_styles(self.ui.soundStartDoubleSpinBox)
        self.update_element_styles(self.ui.soundEndDoubleSpinBox)

    def update_element_styles(self, element):
        element.style().unpolish(element)
        element.style().polish(element)
        element.update()

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

        self.update_element_styles(current_spin_box)

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

        self.ui.Radar_Green.setPixmap(base_pixmap)

    def draw_radar_section(self, angle):
        base_pixmap = QPixmap(self.ui.Radar.size())
        base_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(base_pixmap.width(), base_pixmap.height())
        center = QPointF(base_pixmap.width() / 2, base_pixmap.height() / 2)

        # Малюємо градієнтний промінь
        gradient = QConicalGradient(center, -angle)

        if self.is_warning:
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
            # Якщо фон ще не збережений — збережи його перед першим малюванням точки
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

        if self.is_warning == True:
            self.clear_radar_dots()
            self.is_warning = False

        else:
            self.create_radar_dot(45, 200)
            self.is_warning = True

    def update_wifi_signal_info(self):
        wifi_strength = self.get_wifi_signal_strength()
        print("wifi_signal_strength:", wifi_strength)

        wifi_level = 0

        if wifi_strength:
            wifi_level = math.ceil(wifi_strength / 25)

        self.ui.WiFi_level.setProperty("level", wifi_level)
        self.update_element_styles(self.ui.WiFi_level)

    def get_wifi_signal_strength(self):
        """
        Повертає рівень сигналу Wi-Fi у %, або None якщо не вдалося визначити.
        Підтримує Windows та Linux.
        """
        system = platform.system().lower()

        try:
            if "windows" in system:
                # --- Windows ---
                output = subprocess.check_output(
                    ["netsh", "wlan", "show", "interfaces"], encoding="utf-8"
                )
                match = re.search(r"Signal\s*:\s*(\d+)%", output)
                if match:
                    return int(match.group(1))

            elif "linux" in system:
                # --- Linux ---
                # Спроба через nmcli (нові системи)
                try:
                    output = subprocess.check_output(
                        ["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi"],
                        encoding="utf-8",
                    )
                    for line in output.splitlines():
                        if line.startswith("yes:"):
                            parts = line.split(":")
                            if len(parts) >= 3:
                                return int(parts[2])
                except FileNotFoundError:
                    # Якщо nmcli недоступний, fallback на iwconfig
                    output = subprocess.check_output(["iwconfig"], encoding="utf-8")
                    match = re.search(r"Signal level=(-?\d+) dBm", output)
                    if match:
                        dbm = int(match.group(1))
                        quality = 2 * (dbm + 100)
                        return max(0, min(100, quality))

        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            print(f"⚠️ Error reading Wi-Fi signal: {e}")

        return None

    def closeEvent(self, event):
        print("Закриття програми...")

        event.accept()
