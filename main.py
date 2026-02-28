from Classes.Map_grid import FireGrid
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.WeatherDataSetup import WeatherDataSetup

# Just for testing purposes

if __name__ == '__main__':
    # Testing data
    southLat = 42.817816
    westLon = -80.633052
    gridSize = 100
    cellResolution = 2
    coarseResolution = 10
    cache = True

    # Testing Map_grid
    # fireGrid = FireGrid(south=23.70,north=23.90,west=90.35,east=90.50,rows=60,cols=60)
    # fireGrid.show_map()

    # Testing WeatherDataSetup
    weatherSetup = WeatherDataSetup(42.817816, -80.633052, 100, 2, 10, True)
    weatherLayers = weatherSetup.CreateWeatherLayers()
    print("Weather grid data done")

    # Testing TerrainDataSetup
    terrainSetup = TerrainDataSetup(southLat, westLon, gridSize, cellResolution)
    terrainLayers = terrainSetup.CreateTerrainLayers()
    print("done")


