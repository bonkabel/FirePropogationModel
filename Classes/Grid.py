import numpy as np

class Grid:
    """
    Holds information for the fire simulation in the form of 2D arrays.
    Meant to be populated with data from WeatherDataSetup, TerrainDataSetup, and Fire_Spread, then passed to a simulation class
    """

    # State constants
    UNBURNED = 0
    BURNING = 1
    BURNED_OUT = 2

    def __init__(self, gridSize, cellSize, weatherData, terrainData, rosData, wsvData, razData, ffData, isiData):
        """

        :param gridSize: Number of cells along each axis of the grid
        :param cellSize: Cell width in kilometers, stored in meters
        :param weatherData: Dict from WeatherDataSetup
        :param terrainData: Dict from TerrainDataSetup
        :param rosData: 2D float array, Rate of spread m/s
        :param wsvData: 2D float array, net effective wind speed km/h
        :param razData: 2D float array, net effective wind direction (degrees)
        :param ffData: 2D float array, fine fuel moisture function
        :param isiData: 2D float array, Initial spread index
        """
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