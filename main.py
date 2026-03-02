from Classes.Grid import Grid
from Classes.Map_grid import FireGrid
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.WeatherDataSetup import WeatherDataSetup

# Just for testing purposes

if __name__ == '__main__':
    # Testing data
    southLat = 42.817816 # latitude
    westLon = -80.633052 # longitude
    gridSize = 100 #km
    cellResolution = 2 #km
    coarseResolution = 10 #km
    cache = True

    # Testing Map_grid
    # fireGrid = FireGrid(south=23.70,north=23.90,west=90.35,east=90.50,rows=60,cols=60)
    # fireGrid.show_map()

    # Testing WeatherDataSetup
    weatherSetup = WeatherDataSetup(42.817816, -80.633052, 100, 2, 10, True, False, True)
    weatherLayers = weatherSetup.CreateWeatherLayers()
    print("Weather grid data done")

    # Testing TerrainDataSetup
    terrainSetup = TerrainDataSetup(southLat, westLon, gridSize, cellResolution)
    terrainLayers = terrainSetup.CreateTerrainLayers()
    print("Terrain grid data done")

    # Testing Grid
    grid = Grid(weatherLayers, terrainLayers, gridSize)
    print("Grid setup")


