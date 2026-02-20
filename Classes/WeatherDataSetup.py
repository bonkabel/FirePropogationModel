import math
import numpy as np
import openmeteo_requests
import requests_cache
from retry_requests import retry
from scipy.ndimage import zoom

class WeatherDataSetup:
    def __init__(self, southLat, westLon, gridSize, cellResolution, coarseResolution, cache):
        """
        Creates a geographic weather grid, gets coarse weather data from open-meteo, and interpolates it to a finer resolution

        :param southLat: latitude of the bottom edge of the grid in degrees, southern boundary of the area
        :param westLon: longitude of the left edge of the grid in degrees, western boundary of the area
        :param gridSize: number of cells per side of the final fine resolution grid. Resulting grid will have the resolution (gridSize x gridSize)
        :param cellResolution: Size of each fine grid cell in kilometres. Ex: 1.0 would mean a grid cell represents 1 km x 1 km
        :param coarseResolution: Resolution of the coarse grid before interpolation. Determines what is retrieved from the API
        :param cache: Boolean value indicating whether API request caching and retry logic should be enabled
        """

        self.southLat = southLat
        self.westLon = westLon

        self.gridSize = gridSize
        self.cellResolution = cellResolution
        self.modelResolution = coarseResolution

        self.cache = cache

        self.latStep = cellResolution / 111
        self.lonStep = cellResolution / (111 * math.cos(math.radians(southLat)))

        scale = coarseResolution / cellResolution
        self.coarseSize = int(gridSize / scale)

        self.latStepCoarse = coarseResolution / 111
        self.lonStepCoarse = coarseResolution / (111 * math.cos(math.radians(southLat)))

        self.coarsePoints = self._GenerateCoarseGridPoints()
        self.gridPoints = self._GenerateGridPoints()

        self.client = self._CreateClient()

    def _GenerateCoarseGridPoints(self):
        """
        Generates latitude and longitude coordinate pairs for each cell in the coarse resolution grid

        :return: List of (latitude, longitude) tuples representing each coarse grid cell location
        """
        points = []

        for i in range(self.coarseSize):
            for j in range(self.coarseSize):
                latitude = self.southLat + i * self.latStepCoarse
                longitude = self.westLon + j * self.lonStepCoarse
                points.append((latitude, longitude))

        return points

    def _GenerateGridPoints(self):
        """
        Generates latitude and longitude coordinate pairs for each cell in the fine resolution grid

        :return: List of (latitude, longitude) tuples representing each fine grid cell location
        """
        points = []

        for i in range(self.gridSize):
            for j in range(self.gridSize):
                latitude = self.southLat + i * self.latStep
                longitude = self.westLon + j * self.lonStep
                points.append((latitude, longitude))

        return points

    def _CreateClient(self):
        """
        Creates and returns on open-meteo client

        If caching is enbled, wraps the session with cache and retry logic to reduce redundant requests and handle failures

        :return: Configured openmeteo_requests.Client instance
        """
        if self.cache:
            cacheSession = requests_cache.CachedSession('.cache', expire_after=3600)
            retrySession = retry(cacheSession, retries=8, backoff_factor=1)
            return openmeteo_requests.Client(session=retrySession)
        else:
            return openmeteo_requests.Client()


    def _Upscaledata(self, coarseData):
        """
        Interpolates coarse grid weather data to match the fine grid size

        Use bilinear interpolation to scale each 2D weather array

        :param coarseData: Dictionary mapping weather variable names to 2D NumPy arrays at coarse resolution.
        :return: Dictionary mapping weather variable names to @d NumPy arrays at fine resolution
        """
        scaleFactor = self.gridSize / self.coarseSize

        fineData = {}

        for key in coarseData:
            fineData[key] = zoom(coarseData[key], scaleFactor, order=1)

        return fineData

    def CreateGrid(self):
        """
        Fetches weather data for all coarse grid points in batches.
        Stores the results in 2D arrays.
        Interpolates them to a finer resolution

        :return: Dictionary containing fine resolution 2D NumPy arrays for reach weather variable
        """
        batchSize = 125

        coarseData = {
            "temperature": np.zeros((self.coarseSize, self.coarseSize)),
            "humidity": np.zeros((self.coarseSize, self.coarseSize)),
            "precipitation": np.zeros((self.coarseSize, self.coarseSize)),
            "wind_speed": np.zeros((self.coarseSize, self.coarseSize)),
            "wind_direction": np.zeros((self.coarseSize, self.coarseSize))
        }


        for batch in range(0, len(self.coarsePoints), batchSize):
            latlong = self.coarsePoints[batch:batch + batchSize]

            lats = [i[0] for i in latlong]
            longs = [i[1] for i in latlong]

            params = {
                "latitude": lats,
                "longitude": longs,
                "current_weather": True,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "wind_direction_10m"
                ]
            }

            responses = self.client.weather_api("https://api.open-meteo.com/v1/forecast", params=params)

            for index, response in enumerate(responses):
                i = batch + index

                row = i // self.coarseSize
                col = i % self.coarseSize

                hourly = response.Hourly()

                coarseData["temperature"][row][col] = hourly.Variables(0).ValuesAsNumpy()[0]
                coarseData["humidity"][row][col] = hourly.Variables(1).ValuesAsNumpy()[0]
                coarseData["precipitation"][row][col] = hourly.Variables(2).ValuesAsNumpy()[0]
                coarseData["wind_speed"][row][col] = hourly.Variables(3).ValuesAsNumpy()[0]
                coarseData["wind_direction"][row][col] = hourly.Variables(4).ValuesAsNumpy()[0]



        return self._Upscaledata(coarseData)