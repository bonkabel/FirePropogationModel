import numpy as np

from Classes.Fire_Spread import Fire_Spread
from Classes.Grid import Grid
from Classes.MTTSimulation import MTTSimulation
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.WeatherDataSetup import WeatherDataSetup

class SimulationRunner:
    """
    Backend wrapper that encompasses the full fire simulation pipeline.
    Independent of any UI framework
    """

    def __init__(self, lat, lon, gridSize, cellResolution=2):
        self.lat = lat
        self.lon = lon
        self.gridSize = gridSize
        self.cellResolution = cellResolution

        self.weatherLayers = None
        self.terrainLayers = None
        self.terrainSetup = None
        self.simulation = None
        self.ros = self.wsv = self.raz = self.ff = self.isi = None

    def run(self, numIgnitions=10, dt=3600, weatherMode="current", cacheData=False, useCachedData=False):
        weatherSetup = WeatherDataSetup(self.lat, self.lon, self.gridSize, self.cellResolution, 10, False, cacheData, useCachedData)
        self.weatherLayers = weatherSetup.CreateWeatherLayers(weatherMode)

        terrainSetup = TerrainDataSetup(self.lat, self.lon, self.gridSize, self.cellResolution)
        self.terrainLayers = terrainSetup.CreateTerrainLayers()

        fireSpread = Fire_Spread(
            self.weatherLayers['humidity'],
            self.weatherLayers['wind_speed'],
            self.weatherLayers['wind_direction'],
            self.weatherLayers['precipitation'],
            self.weatherLayers['temperature'],
            self.terrainLayers['trees'],
            self.terrainLayers['slope_magnitude'],
            self.terrainLayers['slope_direction']
        )
        self.ros, self.wsv, self.raz, self.ff, self.isi = fireSpread.roscalculation()

        grid = Grid(self.gridSize, self.cellResolution, self.weatherLayers, self.terrainLayers,
                    self.ros, self.wsv, self.raz, self.ff, self.isi)



        self.simulation = MTTSimulation(grid, dt=dt)
        self.simulation.IgniteRandom(numIgnitions)
        self.simulation.Solve()

        self.terrainSetup = terrainSetup  # kept for lat/lon bounds

    def getMeanWindDirection(self):
        wd = self.weatherLayers['wind_direction']
        return np.degrees(np.arctan2(
            np.sin(np.radians(wd)).mean(),
            np.cos(np.radians(wd)).mean()
        )) % 360

    def getMeanSpreadDirection(self):
        raz = self.raz
        return np.degrees(np.arctan2(
            np.sin(np.radians(raz)).mean(),
            np.cos(np.radians(raz)).mean()
        )) % 360

    def getMeanSlopeDirection(self):
        sd = self.terrainLayers['slope_direction']
        return np.degrees(np.arctan2(
            np.sin(np.radians(sd)).mean(),
            np.cos(np.radians(sd)).mean()
        )) % 360

    def getStats(self):
        return {
            "mean_temperature": self.weatherLayers['temperature'].mean(),
            "mean_humidity": self.weatherLayers['humidity'].mean(),
            "mean_wind_speed": self.weatherLayers['wind_speed'].mean(),
            "mean_wind_direction": self.getMeanWindDirection(),
            "mean_precipitation": self.weatherLayers['precipitation'].mean(),
            "mean_ros": self.ros.mean(),
            "mean_isi": self.isi.mean(),
            "mean_spread_direction": self.getMeanSpreadDirection(),
            "mean_slope_direction": self.getMeanSlopeDirection()
        }