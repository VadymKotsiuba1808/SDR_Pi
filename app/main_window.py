# -*- coding: utf-8 -*-
import math
from PyQt5.QtWidgets import QMainWindow

from PyQt5.QtCore import QTimer, QDateTime, Qt, QRect, QThread
from PyQt5.QtGui import QPixmap, QTransform, QPainter, QColor, QPen
from PyQt5 import uic

from app.services.api_server import ApiServer
from app.services.map_service import MapService, MapTypes
from app.core.signal_analyzer import SignalAnalyzer
from app.utils.test_data_provider import TestDataProvider
from app.assets import resources_rc

class MainWindow(QMainWindow):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        
        uic.loadUi("app/ui/main_window.ui", self)
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        self.signal_analyzer = SignalAnalyzer()
        self.test_data_provider = TestDataProvider()
        self.map_service = MapService(api_key=self.settings.get('maps', 'api_key', fallback=''))
        
        self.api_server = ApiServer(signal_analyzer=self.signal_analyzer)
        
        self._setup_timers()
        self._setup_state_variables()
        self._connect_signals_and_start_threads()
        
        self.Radar_Red.hide()
        self.change_map_type()
        print("Головне вікно успішно ініціалізовано.")

    def _setup_timers(self):
        self.timer_1sec = QTimer(self)
        self.timer_1sec.timeout.connect(self.update_time_and_date)
        self.timer_1sec.start(1000)
        
        self.timer_radar = QTimer(self)
        self.timer_radar.timeout.connect(self.rotate_radar_animation)
        self.timer_radar.start(60)
        
        self.test_update_timer = QTimer(self)
        self.test_update_timer.timeout.connect(self.update_status_bar_with_test_data)
        self.test_update_timer.start(2000)

    def _setup_state_variables(self):
        self.current_map_type_index = 0
        self.map_types = [MapTypes.ROAD, MapTypes.SATELLITE, MapTypes.TERRAIN, MapTypes.HYBRID]
        self.current_coords = [49.83, 24.03]

    def _connect_signals_and_start_threads(self):
        """З'єднує сигнали та запускає фонові потоки."""
        # Кнопки
        self.mapLayoutButton.clicked.connect(self.change_map_type)
        self.screenSaveButton.clicked.connect(self.take_screenshot)
        self.homeButton.clicked.connect(self.update_status_bar_with_test_data)
        self.menuButton.clicked.connect(self.test_draw_dot)

        self.api_thread = QThread()
        self.api_server.moveToThread(self.api_thread)
        
        # Коли потік стартує, викликаємо метод, що запускає Flask
        self.api_thread.started.connect(self.api_server.start_server)
        
        # Підключаємо сигнали від сервера до обробників у цьому вікні
        self.api_server.rf_data_received.connect(self.handle_rf_data)
        self.api_server.audio_alert_received.connect(self.handle_audio_alert)
        
        # Запускаємо потік
        self.api_thread.start()

    # --- Обробники сигналів (слоти) ---
    
    def handle_rf_data(self, analyzed_results):
        print(f"Слот отримав проаналізовані RF дані: {analyzed_results}")
        self.flush_radar_dots()
        if analyzed_results:
            if '0' in analyzed_results: self.create_radar_dot(180, 350)
            if '1' in analyzed_results: self.create_radar_dot(240, 150)
    
    def handle_audio_alert(self, status):
        print(f"Слот отримав звукову тривогу: {status}")
        self.Sound_alert.setProperty("alert", status)

    # --- Методи для оновлення UI ---

    def update_time_and_date(self):
        current_datetime = QDateTime.currentDateTime()
        self.DateLabel.setText(current_datetime.toString("dd.MM.yyyy"))
        self.TimeLabel.setText(current_datetime.toString("hh:mm:ss"))

    def rotate_radar_animation(self):
        transform = QTransform()
        current_angle = getattr(self, 'radar_angle', 0)
        current_angle = (current_angle + 6) % 360
        transform.rotate(current_angle)
        
        original_pixmap = QPixmap(":/images/radar_green.png")
        if original_pixmap.isNull(): return

        rotated_pixmap = original_pixmap.transformed(transform, Qt.SmoothTransformation)
        self.Radar_Green.setPixmap(rotated_pixmap)
        self.radar_angle = current_angle

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

    # --- Методи-дії для кнопок ---

    def change_map_type(self):
        map_type = self.map_types[self.current_map_type_index]
        pixmap = self.map_service.get_map_pixmap(self.current_coords, map_type)
        if pixmap:
            print(f"Карта типу '{map_type.value}' успішно завантажена.")
        
        self.current_map_type_index = (self.current_map_type_index + 1) % len(self.map_types)

    def take_screenshot(self):
        screenshot = self.grab()
        filename = f"screenshot_{QDateTime.currentDateTime().toString('yyyy-MM-dd_hh-mm-ss')}.png"
        screenshot.save(filename, 'png')
        print(f"Знімок екрану збережено як {filename}")

    # --- Тестові методи ---

    def update_status_bar_with_test_data(self):

        data = self.test_data_provider.get_next_test_data()
        self.ghz24_1.setProperty("band_active", data['ghz24_1'])
        self.ghz58_1.setProperty("band_active", data['ghz58_1'])
        self.RF_alert.setProperty("alert", data['rf_alert'])
        self.Sound_alert.setProperty("alert", data['sound_alert'])
        self.current_coords = data['coord']
        print(f"Оновлено тестові дані. Координати: {self.current_coords}")

    def test_draw_dot(self):
        self.create_radar_dot(45, 200)

    def closeEvent(self, event):
        """Коректно завершує роботу фонового потоку при закритті вікна."""
        print("Закриття програми, зупинка сервера та потоку...")
        self.api_server.stop()
        if hasattr(self, 'api_thread') and self.api_thread.isRunning():
            self.api_thread.quit()
            self.api_thread.wait(500) # Чекаємо пів секунди на завершення
        event.accept()

