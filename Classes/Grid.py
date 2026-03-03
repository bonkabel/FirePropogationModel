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


    def __init__(self, weatherData, terrainData, gridSize):


        # Weather
        self.temperature = weatherData['temperature']
        self.humidity = weatherData['humidity']
        self.windSpeed = weatherData['wind_speed']
        self.windDirection = weatherData['wind_direction']

        # Terrain
        self.elevation = terrainData['elevation']
        self.slopeMagnitude = terrainData['slope_magnitude']
        self.slopeDirection = terrainData['slope_direction']
        self.water = terrainData['water']
        self.trees = terrainData['trees']

        # State information
        self.state = np.zeros((gridSize, gridSize), dtype=int)
        self.fireTimer = np.zeros((gridSize, gridSize), dtype=float) # How long the fire has been burning for
        self.ignitionProbability = np.zeros((gridSize, gridSize), dtype=float) # Probability of ignition



        # State information
        self.state = np.zeros((gridSize, gridSize), dtype=int)
        self.fireTimer = np.zeros((gridSize, gridSize), dtype=float) # How long the fire has been burning for
        self.ignitionProbability = np.zeros((gridSize, gridSize), dtype=float) # Probability of ignition