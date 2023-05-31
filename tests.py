from itertools import cycle


class TestCase:
    def __init__(self):
        self.__list_data = []

        self.__list_data.append(
            {
                "gps_level": 80,
                "wifi_level": 65,
                "ghz24_1": True,
                "ghz24_2": True,
                "ghz24_3": True,
                "ghz24_4": True,
                "ghz58_1": True,
                "ghz58_2": True,
                "ghz58_3": True,
                "ghz58_4": True,
                "rf_alert": True,
                "sound_alert": False,
                "coord": [49.8349462, 24.0310315]
            }
        )

        self.__list_data.append(
            {
                "gps_level": 30,
                "wifi_level": 100,
                "ghz24_1": False,
                "ghz24_2": True,
                "ghz24_3": True,
                "ghz24_4": True,
                "ghz58_1": True,
                "ghz58_2": True,
                "ghz58_3": True,
                "ghz58_4": False,
                "rf_alert": False,
                "sound_alert": True,
                "coord": [50.4394956, 30.5573333]
            }
        )

        self.__list_data.append(
            {
                "gps_level": 0,
                "wifi_level": 65,
                "ghz24_1": False,
                "ghz24_2": False,
                "ghz24_3": False,
                "ghz24_4": False,
                "ghz58_1": True,
                "ghz58_2": True,
                "ghz58_3": True,
                "ghz58_4": True,
                "rf_alert": False,
                "sound_alert": False,
                "coord": [49.434112, 27.012607]
            }
        )

        self.__list_data.append(
            {
                "gps_level": 80,
                "wifi_level": 65,
                "ghz24_1": True,
                "ghz24_2": True,
                "ghz24_3": True,
                "ghz24_4": True,
                "ghz58_1": True,
                "ghz58_2": True,
                "ghz58_3": True,
                "ghz58_4": True,
                "rf_alert": True,
                "sound_alert": False,
                "coord": [50.353026, 30.511801]
            }
        )

        self.__cycle_list = cycle(self.__list_data)

    def next_test(self):
        return next(self.__cycle_list)