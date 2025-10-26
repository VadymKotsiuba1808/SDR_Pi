import math
import asyncio
from PyQt6.QtWidgets import QMainWindow, QApplication, QDialog
from PyQt6.QtCore import QTimer, QDateTime, Qt, QPointF
from PyQt6.QtGui import QPixmap, QConicalGradient, QPainter, QColor, QPen
from PyQt6 import uic
from qasync import asyncSlot
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

        uic.loadUi("app/ui/main_window.ui", self)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.is_warning = False

        self.test_data_provider = TestDataProvider()

        self.map_service = MapService(settings=self.settings_service)

        self.api_server = ApiServer(settings=self.settings_service)

        # 2. Передаємо йому методи з MainWindow як callback-функції
        self.api_server.on_rf_data = self.handle_rf_data
        self.api_server.on_audio_alert = self.handle_audio_alert

        self._setup_timers()
        self._setup_state_variables()

        self.mapLayoutButton.clicked.connect(self.change_map_type)
        self.screenSaveButton.clicked.connect(self.take_screenshot)
        self.homeButton.clicked.connect(self.update_status_bar_with_test_data)
        self.addMapButton.clicked.connect(self.open_set_map_dialog)
        self.menuButton.clicked.connect(self.test_draw_dot)

        self.saveRadarSettingsBtn.clicked.connect(self.handle_radar_radius_change)

        radar_max_radius = self.settings_service.radar_max_radius
        self.radarRadiusSpinbox.setRange(1, radar_max_radius)

        radar_radius = self.settings_service.radar_radius
        self.radarRadiusSpinbox.setValue(radar_radius)

        self.Radar_Red.hide()

        self.start_async_tasks()

        print("Головне вікно успішно ініціалізовано.")

    def showEvent(self, event):
        """
        Викликається, коли віджет показується.
        Використовуємо для первинного розрахунку геометрії.
        """
        super().showEvent(event)
        self.map_background_label.setScaledContents(False)
        # Робимо розрахунок при першому показі
        self._update_map_geometry()
        self.refresh_map()

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

    def _setup_timers(self):
        self.timer_1sec = QTimer(self)
        self.timer_1sec.timeout.connect(self.update_time_and_date)
        self.timer_1sec.start(1000)

        self.timer_radar = QTimer(self)
        self.timer_radar.timeout.connect(self.rotate_radar_animation)
        self.timer_radar.start(60)

        self.test_update_timer = QTimer(self)
        # Важливо: під'єднуємо таймер до асинхронного слота
        self.test_update_timer.timeout.connect(self.update_status_bar_with_test_data)
        self.test_update_timer.start(10 * 60 * 1000)

    def _setup_state_variables(self):
        self.current_map_type_index = 0
        self.map_types = [e for e in MapTypes]
        self.current_coords = [49.43440, 27.00543]

    def _update_map_geometry(self):
        """
        Обчислює та оновлює коефіцієнти та зміщення
        на основі ПОТОЧНИХ розмірів віджетів.
        (з розширеним логуванням)
        """

        # Перевірка, чи віджети вже завантажені
        if not self.Radar.width() or not self.Radar.height():
            return

        # --- 1. Збір вхідних даних ---
        radar_width = self.RadarFrame.width()
        radar_height = self.RadarFrame.height()

        map_bg_width = self.map_background_label.width()
        map_bg_height = self.map_background_label.height()

        # --- 2. Розрахунок коефіцієнтів ---
        self.add_sizes_map_k = [
            map_bg_width / radar_width,
            map_bg_height / radar_height,
        ]

    # --- Обробники даних, які викликаються з асинхронних функцій ---
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
        self.Sound_alert.setProperty("alert", status)

    def handle_radar_radius_change(self):
        new_radar_radius = self.radarRadiusSpinbox.value()
        self.settings_service.radar_radius = new_radar_radius
        self.scale_map()

    def open_set_map_dialog(self):

        # 1. Створюємо екземпляр діалогу
        self.dialog = SetMapDialog(
            settings=self.settings_service, add_sizes_map_k=self.add_sizes_map_k
        )

        # 2. "Загортаємо" його (якщо make_scalable приймає QDialog)
        ScalableDialog = make_scalable(QDialog)
        self.scalable_dialog = ScalableDialog(widget_to_scale=self.dialog)

        # 3. Використовуємо .exec() для блокуючого виклику
        # .exec() покаже вікно і ЗАЧЕКАЄ, доки користувач натисне "Зберегти" або "Скасувати"
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

            print("ГОЛОВНЕ ВІКНО: Отримано налаштування!", settings_data)
            # ... тут ваш код обробки 'settings_data' ...
            # Наприклад: self.my_map_pixmap = settings_data["pixmap"]

        else:
            # Якщо користувач натиснув "Скасувати" або закрив вікно
            print("ГОЛОВНЕ ВІКНО: Налаштування скасовано.")

        # 6. Очищуємо посилання
        self.scalable_dialog = None

    # --- Методи для оновлення UI (залишаються без змін) ---
    def update_time_and_date(self):
        current_datetime = QDateTime.currentDateTime()
        self.DateLabel.setText(current_datetime.toString("dd.MM.yyyy"))
        self.TimeLabel.setText(current_datetime.toString("hh:mm:ss"))

    def rotate_radar_animation(self):
        current_angle = getattr(self, "radar_angle", 0)
        current_angle = (current_angle + 6) % 360
        self.radar_angle = current_angle

        base_pixmap = self.draw_radar_section(current_angle)

        self.Radar_Green.setPixmap(base_pixmap)

    def draw_radar_section(self, angle):
        base_pixmap = QPixmap(self.Radar.size())
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
        self.Radar.setPixmap(QPixmap(":/images/radar.png"))

    def create_radar_dot(self, angle, distance):
        pixmap = self.Radar.pixmap()
        self.radar_background = self.Radar.pixmap()
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
        self.Radar.setPixmap(pixmap)

    def clear_radar_dots(self):
        """Видаляє намальовані точки з радара, відновлюючи фон."""
        if not hasattr(self, "radar_background"):
            # Якщо фон ще не збережений — збережи його перед першим малюванням точки
            return

        clean_pixmap = self.radar_background.copy()
        self.Radar.setPixmap(clean_pixmap)

    # --- Асинхронні слоти (залишаються без змін) ---
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
        pixmap = self.current_map
        current_radius_px = self.current_map_radius
        if pixmap:
            radar_radius_m = self.settings_service.radar_radius  # у метрах
            radar_max_radius_m = self.settings_service.radar_max_radius  # у метрах
            radius_px = self.RadarFrame.width() / 2  # піксельний розмір радара

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
            self.map_background_label.setPixmap(scaled_pixmap)
            self.map_background_label.resize(scaled_pixmap.size())

            # Отримуємо центр радара
            radar_center = self.RadarFrame.geometry().center()

            # Отримуємо центр зображення
            pixmap_center = self.map_background_label.rect().center()

            # Розраховуємо нову позицію для QLabel, щоб центри співпали
            new_x = radar_center.x() - pixmap_center.x()
            new_y = radar_center.y() - pixmap_center.y()

            # Переміщуємо фон карти
            self.map_background_label.move(new_x, new_y)
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
        self.ghz24_1.setProperty("band_active", data["ghz24_1"])
        self.ghz58_1.setProperty("band_active", data["ghz58_1"])
        self.RF_alert.setProperty("alert", data["rf_alert"])
        self.Sound_alert.setProperty("alert", data["sound_alert"])
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

    def closeEvent(self, event):
        print("Закриття програми...")

        event.accept()
