from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QDateTime, QTimer
from PyQt5.QtGui import QScreen

from UI.SDR_UI import Ui_MainWindow
from gmap import get_map, MapTypes

import sys


class MyUiWindow(QMainWindow):

    def __init__(self):
        super(MyUiWindow, self).__init__()
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        #self.showFullScreen()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.mapLayoutButton.clicked.connect(self.change_map_action)
        self.ui.screenSaveButton.clicked.connect(self.take_screenshot)

        self.__current_map = 0
        self.__current_date = "15.12.2022"
        self.__current_time = "00:00:00"
        self.change_map_action()

        timer_1sec = QTimer(self)
        timer_1sec.timeout.connect(self.update_date_time)
        timer_1sec.start(1000)

    def update_date_time(self):
        date, self.__current_time = QDateTime().currentDateTime().toString(QtCore.Qt.DateFormat.ISODate).split('T')
        self.__current_date = '.'.join(date.split('-')[::-1])
        self.ui.DateLabel.setText( self.__current_date)
        self.ui.TimeLabel.setText(self.__current_time)

    def change_map_action(self) -> bool:
        if self.__current_map == 0 or self.__current_map == MapTypes.HYBRID:
            self.__current_map = MapTypes.ROAD
        elif self.__current_map == MapTypes.ROAD:
            self.__current_map = MapTypes.SATELLITE
        elif self.__current_map == MapTypes.SATELLITE:
            self.__current_map = MapTypes.TERRAIN
        elif self.__current_map == MapTypes.TERRAIN:
            self.__current_map = MapTypes.HYBRID

        if self.__current_map in MapTypes:
            get_map([49.8349462, 24.0310315], self.__current_map)
            self.setStyleSheet("background-image: url(temp_data/current_map.png);")
            return True
        return False

    def take_screenshot(self):
        shoot = QApplication.primaryScreen().grabWindow(self.winId(), 0, 0, 1920, 1080)
        filename = f"screenshoots/{self.__current_date.replace('.','-')}-{self.__current_time}.jpg"
        shoot.save(filename, 'jpg')
        print("Screenshot taken")


if __name__ == "__main__":
    app = QApplication([])
    application = MyUiWindow()
    application.show()
    sys.exit(app.exec_())
