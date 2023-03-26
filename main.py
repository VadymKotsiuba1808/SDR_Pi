from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QDateTime, QTime, QTimer, QRect
from PyQt5.QtGui import QTransform, QPixmap

from UI.SDR_UI import Ui_MainWindow
from gmap import get_map, MapTypes
from tests import TestCase

import sys, itertools

def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class MyUiWindow(QMainWindow):

    def __init__(self):
        super(MyUiWindow, self).__init__()
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # self.showFullScreen()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.mapLayoutButton.clicked.connect(self.change_map_type_action)
        self.ui.screenSaveButton.clicked.connect(self.take_screenshot)
        self.ui.onTimerButton.clicked.connect(self.start_jammer)
        self.ui.offTimerButton.clicked.connect(self.stop_jammer)
        self.ui.homeButton.clicked.connect(self.update_status_bar)

        self.ui.k_label_1.setEnabled(False)
        self.ui.Radar_Red.hide()

        self.__current_map = 0
        self.__current_date = "15.12.2022"
        self.__current_time = "00:00:00"
        self.__current_coord = [0.0, 0.0]
        self.__flag_jammer = False

        self.timer_1sec = QTimer(self)
        self.timer_1sec.timeout.connect(self.handler_1sec)
        self.timer_1sec.start(1000)

        self.change_map_type_action()
        self.timer_refresh = QTimer(self)
        self.timer_refresh.timeout.connect(self.refresh)
        self.timer_refresh.start(20)

        self.__angle_cycle = itertools.cycle([i for i in range(0, 361, 10)])
        self.timer_radar = QTimer(self)
        self.timer_radar.timeout.connect(self.__rotate_radar)
        self.timer_radar.start(60)

        self.__test_values = TestCase()

    def __rotate_radar(self):
        original_pixmap = QPixmap(":/Images/images/radar_green.png")
        transform = QTransform()
        transform.rotate(next(self.__angle_cycle))
        temp_pixmap = original_pixmap.transformed(transform, Qt.SmoothTransformation)
        width, height = original_pixmap.size().width(), original_pixmap.size().height()
        center_x = temp_pixmap.width() // 2
        center_y = temp_pixmap.height() // 2
        rect_x = center_x - width // 2
        rect_y = center_y - height // 2
        temp_pixmap = temp_pixmap.copy(QRect(rect_x, rect_y, width, height))
        self.ui.Radar_Green.setPixmap(temp_pixmap)
        del temp_pixmap

    def refresh(self):
        self.setStyleSheet("background-image: url(temp_data/current_map.png);")

    def update_status_bar(self):
        data = self.__test_values.next_test()
        self.ui.GPS_level.setProperty("level", int(remap(data['gps_level'], 0, 100, 0, 4)))
        self.ui.WiFi_level.setProperty("level", int(remap(data['wifi_level'], 0, 100, 0, 4)))
        self.ui.ghz24_1.setProperty("band_active", data['ghz24_1'])
        self.ui.ghz24_2.setProperty("band_active", data['ghz24_2'])
        self.ui.ghz24_3.setProperty("band_active", data['ghz24_3'])
        self.ui.ghz24_4.setProperty("band_active", data['ghz24_4'])
        self.ui.ghz58_1.setProperty("band_active", data['ghz58_1'])
        self.ui.ghz58_2.setProperty("band_active", data['ghz58_2'])
        self.ui.ghz58_3.setProperty("band_active", data['ghz58_3'])
        self.ui.ghz58_4.setProperty("band_active", data['ghz58_4'])
        self.ui.RF_alert.setProperty("alert", data['rf_alert'])
        self.ui.Sound_alert.setProperty("alert", data['sound_alert'])
        self.__current_coord = data['coord']
        self.refresh_map()

    def start_jammer(self):
        minutes = 2
        self.ui.TimerTime.setText('{:02d}:{:02d}:00'.format(*divmod(minutes, 60)))
        self.__flag_jammer = True
        self.ui.k_label_1.setEnabled(True)
        self.ui.onTimerButton.setEnabled(False)
        QTimer.singleShot(minutes * 60 * 1000, self.stop_jammer)

    def stop_jammer(self):
        self.ui.TimerTime.setText('00:00:00')
        self.__flag_jammer = False
        self.ui.k_label_1.setEnabled(False)
        self.ui.onTimerButton.setEnabled(True)
        print("Jammer Timer Handled")

    def handler_1sec(self):
        date, self.__current_time = QDateTime().currentDateTime().toString(QtCore.Qt.DateFormat.ISODate).split('T')
        self.__current_date = '.'.join(date.split('-')[::-1])
        self.ui.DateLabel.setText(self.__current_date)
        self.ui.TimeLabel.setText(self.__current_time)

        if self.__flag_jammer:
            self.ui.TimerTime.setText(
                QTime().fromString(self.ui.TimerTime.text(), "hh:mm:ss").addSecs(-1).toString("hh:mm:ss"))

    def refresh_map(self) -> bool:
        if self.__current_map in MapTypes:
            get_map(self.__current_coord, self.__current_map)
            self.setStyleSheet("background-image: url(temp_data/current_map.png);")
            return True
        return False

    def change_map_type_action(self) -> bool:
        if self.__current_map == 0 or self.__current_map == MapTypes.HYBRID:
            self.__current_map = MapTypes.ROAD
        elif self.__current_map == MapTypes.ROAD:
            self.__current_map = MapTypes.SATELLITE
        elif self.__current_map == MapTypes.SATELLITE:
            self.__current_map = MapTypes.TERRAIN
        elif self.__current_map == MapTypes.TERRAIN:
            self.__current_map = MapTypes.HYBRID

        return self.refresh_map()

    def take_screenshot(self):
        shoot = QApplication.primaryScreen().grabWindow(self.winId(), 0, 0, 1920, 1080)
        filename = f"screenshoots/{self.__current_date.replace('.', '-')}-{self.__current_time}.jpg"
        shoot.save(filename, 'jpg')
        print("Screenshot taken")


if __name__ == "__main__":
    app = QApplication([])
    application = MyUiWindow()
    application.show()
    sys.exit(app.exec_())
