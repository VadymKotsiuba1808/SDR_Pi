# app/main_window.py
import math
import asyncio
from PyQt6.QtWidgets import QMainWindow,QApplication
from PyQt6.QtCore import QTimer, QDateTime, Qt, QPointF
from PyQt6.QtGui import QPixmap, QConicalGradient, QPainter, QColor, QPen
from PyQt6 import uic
from qasync import asyncSlot
from app.assets import resources_rc

from app.services.api_server import ApiServer 
from app.services.map_service import MapService, MapTypes
from app.utils.test_data_provider import TestDataProvider
from app.services.settings_service import SettingsService

class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings
        
        uic.loadUi("app/ui/main_window.ui", self)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        
        # self.signal_analyzer = SignalAnalyzer()
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
        self.menuButton.clicked.connect(self.test_draw_dot)
        
        self.Radar_Red.hide()

        self.start_async_tasks()
        
        print("Головне вікно успішно ініціалізовано.")

    @asyncSlot()
    async def start_async_tasks(self):
        """
        Запускає всі фонові асинхронні задачі.
        Цей метод має викликатися з 'main' ПІСЛЯ створення вікна.
        """
        print("Запуск фонових асинхронних задач (сервер та слухач)...")
        self.api_server.run_server()
        self.listen_for_pi_data()
        self.refresh_map()

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
        self.map_types = [MapTypes.ROAD, MapTypes.SATELLITE, MapTypes.TERRAIN, MapTypes.HYBRID]
        self.current_coords = [49.83, 24.03]

    # --- Обробники даних, які тепер викликаються з асинхронних функцій ---
    def handle_rf_data(self, analyzed_results):
        print(f"Слот отримав проаналізовані RF дані: {analyzed_results}")
        self.flush_radar_dots()
        if analyzed_results:
            if '0' in analyzed_results: self.create_radar_dot(180, 350)
            if '1' in analyzed_results: self.create_radar_dot(240, 150)
    
    def handle_audio_alert(self, status):
        print(f"Слот отримав звукову тривогу: {status}")
        self.Sound_alert.setProperty("alert", status)

    # --- Методи для оновлення UI (залишаються без змін) ---
    def update_time_and_date(self):
        current_datetime = QDateTime.currentDateTime()
        self.DateLabel.setText(current_datetime.toString("dd.MM.yyyy"))
        self.TimeLabel.setText(current_datetime.toString("hh:mm:ss"))

    def rotate_radar_animation(self):
        current_angle = getattr(self, 'radar_angle', 0)
        current_angle = (current_angle + 6) % 360
        self.radar_angle = current_angle

        base_pixmap=self.draw_radar_section(current_angle)

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
        if not pixmap or pixmap.isNull(): return
        
        painter = QPainter(pixmap)
        pen = QPen(QColor('red'), 20)
        painter.setPen(pen)
        
        center_x = pixmap.width() / 2
        center_y = pixmap.height() / 2
        rad_angle = math.radians(angle - 90)
        
        x = center_x + distance * math.cos(rad_angle)
        y = center_y + distance * math.sin(rad_angle)
        
        painter.drawPoint(int(x), int(y))
        painter.end()
        self.Radar.setPixmap(pixmap)

    # --- Асинхронні слоти (залишаються без змін) ---
    @asyncSlot()
    async def refresh_map(self):
        print("Запускаю асинхронне завантаження карти...")
        map_type = self.map_types[self.current_map_type_index]
        pixmap = await self.map_service.get_map_pixmap(self.current_coords, map_type)

        if pixmap:
            print("Карта успішно завантажена.")
            pixmap = pixmap.scaled(
    self.map_background_label.width(),
    self.map_background_label.height(),
    Qt.AspectRatioMode.KeepAspectRatioByExpanding,  # або KeepAspectRatio
    Qt.TransformationMode.SmoothTransformation
)
            self.map_background_label.setPixmap(pixmap)
        else:
            print("Не вдалося завантажити карту.")

    @asyncSlot()
    async def change_map_type(self):
        self.current_map_type_index = (self.current_map_type_index + 1) % len(self.map_types)
        await self.refresh_map()

    def take_screenshot(self):
        screenshot = self.grab()
        filename = f"./screenshots/screenshot_{QDateTime.currentDateTime().toString('yyyy-MM-dd_hh-mm-ss')}.png"
        screenshot.save(filename, 'png')
        print(f"Знімок екрану збережено як {filename}")

    @asyncSlot()
    async def update_status_bar_with_test_data(self):

        data = self.test_data_provider.get_next_test_data()
        self.ghz24_1.setProperty("band_active", data['ghz24_1'])
        self.ghz58_1.setProperty("band_active", data['ghz58_1'])
        self.RF_alert.setProperty("alert", data['rf_alert'])
        self.Sound_alert.setProperty("alert", data['sound_alert'])
        self.current_coords = data['coord']
        print(f"Оновлено тестові дані. Координати: {self.current_coords}")

        await self.refresh_map()

    def test_draw_dot(self):
        self.create_radar_dot(45, 200)

    def closeEvent(self, event):
        print("Закриття програми...")
        
        # Фоново зупиняємо сервер і таски
        # async def shutdown():
        #     await self.api_server.stop_server()
        #     # for task in getattr(self, "async_tasks", []):
        #     #     task.cancel()
        #     # if hasattr(self, "api_server"):
        #     #     await self.api_server.stop_server()
        #     # print("Сервер зупинено. Завершення програми...")

        # # Створюємо таску, не чекаємо її завершення
        # asyncio.create_task(shutdown())
        
        # self.api_server.stop_server()
        event.accept()  # 

