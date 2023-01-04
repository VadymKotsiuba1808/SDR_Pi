from enum import Enum
from PyQt5.QtGui import QPixmap
import requests


class DataConst:
    API_KEY = "AIzaSyAMgV5ZVpjl4nZSBgVx9ajwTAfrdZ-5tS8"
    BASE_URL = "https://maps.googleapis.com/maps/api/staticmap?"
    SIZE = "640x360"
    SCALE = 2


class MapTypes(Enum):
    ROAD = "roadmap"
    SATELLITE = "satellite"
    TERRAIN = "terrain"
    HYBRID = "hybrid"


def get_map(coord: list, maptype: MapTypes, zoom: int = 16):
    name = 'temp_data/current_map.png'
    url = DataConst.BASE_URL + "center=" + str(coord).replace("[", "").replace("]", "") + "&zoom=" + str(zoom) \
          + "&size=" + str(DataConst.SIZE) + "&scale=" + str(DataConst.SCALE) + "&maptype=" + maptype.value + "&key=" \
          + DataConst.API_KEY
    response = requests.get(url)
    with open(name, 'wb') as file:
        file.write(response.content)

    QPixmap(name).scaled(1920, 1080).save(name, quality=100)

    return name