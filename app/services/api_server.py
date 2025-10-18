# -*- coding: utf-8 -*-
from flask import Flask, request
from PyQt6.QtCore import QObject, pyqtSignal
import logging

# ВИПРАВЛЕННЯ: Імпортуємо сам клас, а не стару функцію
from app.core.signal_analyzer import SignalAnalyzer

# Вимикаємо логування Flask у консоль, щоб не засмічувати вивід
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ВИПРАВЛЕННЯ: Клас більше не успадковується від threading.Thread, лише від QObject.
# Тепер це "робітник", якого ми перемістимо в QThread.
class ApiServer(QObject):
    """
    Клас-робітник, що запускає Flask-сервер для прийому
    HTTP-запитів від Raspberry Pi №1.
    """
    # Сигнали, які сервер буде відправляти головному вікну
    rf_data_received = pyqtSignal(list)
    audio_alert_received = pyqtSignal(bool)

    def __init__(self, signal_analyzer: SignalAnalyzer, host='0.0.0.0', port=5000, parent=None):
        super().__init__(parent)
        
        self.flask_app = Flask(__name__)
        self.host = host
        self.port = port
        self.signal_analyzer = signal_analyzer

        # Реєструємо маршрути (endpoints)
        self.flask_app.route('/api/2_4_ghz', methods=['POST'])(self.receive_rf_data)
        self.flask_app.route('/api/audio_alarm', methods=['POST'])(self.receive_audio_alarm)

    def start_server(self):
        """Запускає Flask-сервер. Цей метод буде викликаний, коли потік QThread запуститься."""
        print(f"Flask сервер запущено на http://{self.host}:{self.port}")
        self.flask_app.run(host=self.host, port=self.port)

    def stop(self):
        """Зупиняє сервер (цей метод може не спрацювати надійно, але є спробою)."""
        print("Спроба зупинки Flask сервера...")

    def receive_rf_data(self):
        """Обробник для маршруту /api/2_4_ghz."""
        data_list = request.get_json()
        if data_list:
            analyzed_results = self.signal_analyzer.match(data_list)
            self.rf_data_received.emit(analyzed_results)
        return 'RF data received'

    def receive_audio_alarm(self):
        """Обробник для маршруту /api/audio_alarm."""
        status_data = request.get_json()
        if status_data and 'alert' in status_data:
            alert_status = status_data['alert'].lower() == 'true'
            self.audio_alert_received.emit(alert_status)
        return 'Audio alert received'

