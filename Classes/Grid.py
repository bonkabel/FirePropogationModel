import numpy as np


class Grid:
    """
    Contains information for the fire simulation in the form of 2D arrays.
    Meant for use with data from WeatherDataSetup and TerrainDataSetup
    """
    def __init__(self, weatherData, terrainData):

        self.temperature = weatherData['temperature']
        self.humidity = weatherData['humidity']
        self.windSpeed = weatherData['wind_speed']
        self.windDirection = weatherData['wind_direction']

        self.elevation = terrainData['elevation']
        self.slopeMagnitude = terrainData['slope_magnitude']
        self.slopeDirection = terrainData['slope_direction']
        self.water = terrainData['water']
        self.trees = terrainData['trees']




