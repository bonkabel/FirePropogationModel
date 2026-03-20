import numpy as np

class Grid:
    """
    Holds information for the fire simulation in the form of 2D arrays.
    Meant for use with data from WeatherDataSetup and TerrainDataSetup
    """

    # State constants
    UNBURNED = 0
    BURNING = 1
    BURNED_OUT = 2


    def __init__(self, gridSize, cellSize, weatherData, terrainData, rosData, wsvData, razData, ffData, isiData):

        # Weather
        self.temperature = np.array(weatherData['temperature'], dtype=float)
        self.humidity = np.array(weatherData['humidity'], dtype=float)
        self.windSpeed = np.array(weatherData['wind_speed'], dtype=float)
        self.windDirection = np.array(weatherData['wind_direction'], dtype=float)
        self.precipitation = np.array(weatherData['precipitation'], dtype=float)

        self.gridSize = gridSize
        self.cellSize = cellSize * 1000

        # Terrain
        self.elevation = terrainData['elevation']
        self.slopeMagnitude = terrainData['slope_magnitude']
        self.slopeDirection = terrainData['slope_direction']
        self.water = terrainData['water']
        self.trees = terrainData['trees']

        # Initial spread values
        self.ros = rosData
        self.wsv = wsvData
        self.raz = razData
        self.ff = ffData
        self.isi = isiData

        # State information
        self.state = np.zeros((gridSize, gridSize), dtype=int)
        self.fireTimer = np.zeros((gridSize, gridSize), dtype=float) # How long the fire has been burning for
        self.ignitionProbability = np.zeros((gridSize, gridSize), dtype=float) # Probability of ignition


