def metters_to_pixels(self, distance_m: int, zoom: int, lat: float):
    INITIAL_RESOLUTION = 156543.03392
    meters_per_pixel = (INITIAL_RESOLUTION * math.cos(math.radians(lat))) / (2**zoom)
    return distance_m / meters_per_pixel
