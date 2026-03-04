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

        # Constants for rothermel model
        constants = {
            "C-1" : {
                "trees": "Spruce-Lichen Woodland",
                "a": 90,
                "b": 0.0649,
                "c": 4.5
            },
            "C-2": {
                "trees": "Boreal Spruce",
                "a": 110,
                "b": 0.0282,
                "c": 1.5
            },
            "C-3": {
                "trees": "Mature Jack or Lodgepole Pine",
                "a": 110,
                "b": 0.0444,
                "c": 3.0
            },
            "C-4": {
                "trees": "Immature Jack or Lodgepole Pine",
                "a": 110,
                "b": 0.0293,
                "c": 1.5
            },
            "C-5": {
                "trees": "Red and White Pine",
                "a": 30,
                "b": 0.0697,
                "c": 4.0
            },
            "C-6": {
                "trees": "Conifer Plantation",
                "a": 30,
                "b": 0.0800,
                "c": 3.0
            },
            "C-7": {
                "trees": "Ponderosa Pine-Doughlas-Fir",
                "a": 45,
                "b": 0.0305,
                "c": 2.0
            },
            "D-1": {
                "trees": "Leafless Aspen",
                "a": 30,
                "b": 0.0232,
                "c": 1.6
            },
            "S-1": {
                "trees": "Jack or Lodgepole Pine Slash",
                "a": 75,
                "b": 0.0297,
                "c": 1.3
            },
            "S-2": {
                "trees": "White Spruce-Balsam Slash",
                "a": 40,
                "b": 0.0438,
                "c": 1.7
            },
            "S-3": {
                "trees": "Coastal Cedar-Hemlock-Doughlas-Fir Slash",
                "a": 55,
                "b": 0.0829,
                "c": 3.2
            },
            "O-1": {
                "trees": "Matted Grass",
                "a": 190,
                "b": 0.0310,
                "c": 1.4
            },
            "O-2": {
                "trees": "Dead Grass",
                "a": 250,
                "b": 0.0350,
                "c": 1.7
            }
        }
