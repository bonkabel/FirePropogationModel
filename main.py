import numpy as np

from Classes.Fire_Spread import Fire_Spread
from Classes.Grid import Grid
from Classes.Simulation import Simulation
# from Classes.Map_grid import FireGrid
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.Visualization import Visualization
from Classes.WeatherDataSetup import WeatherDataSetup

# Just for testing purposes

if __name__ == '__main__':

    # Testing data
    southLat = -9.248872 # latitude
    westLon = -45.917065 # longitude
    gridSize = 100 #Dimensions
    cellResolution = 2 #km
    coarseResolution = 10 #km
    cache = True

    # WeatherDataSetup
    weatherSetup = WeatherDataSetup(42.817816, -80.633052, 100, 2, 10, True, True, True)
    weatherLayers = weatherSetup.CreateWeatherLayers()
    print("Weather grid data done")

    # TerrainDataSetup
    terrainSetup = TerrainDataSetup(southLat, westLon, gridSize, cellResolution)
    terrainLayers = terrainSetup.CreateTerrainLayers()
    print("Terrain grid data done")

    # ROS calculation
    fireSpread = Fire_Spread(weatherLayers['humidity'], weatherLayers['wind_speed'], weatherLayers['precipitation'], weatherLayers['temperature'], terrainLayers['trees'])
    rateOfSpread = fireSpread.roscalculation()

    # Grid
    grid = Grid(gridSize, cellResolution, weatherLayers, terrainLayers, rateOfSpread)
    print("Grid setup done")

    # Simulation
    simulation = Simulation(grid, 10, 200)
    simulation.IgniteRandom(10)
    simulation.Run()
    print("Simulation done")

    # Visualization
    viz = Visualization(
        simulation,
        southLat=terrainSetup.southLat,
        westLon=terrainSetup.westLon,
        northLat=terrainSetup.northLat,
        eastLon=terrainSetup.eastLon
    )
    viz.saveTimeline()
    print("Visualization done")













