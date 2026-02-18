import math
import numpy as np
import openmeteo_requests
import requests_cache
from retry_requests import retry
from scipy.ndimage import zoom

class WeatherDataSetup:
    def __init__(self, southLat, westLon, gridSize, cellResolution, modelResolution, cache):
        self.southLat = southLat
        self.westLon = westLon

        self.gridSize = gridSize
        self.cellResolution = cellResolution
        self.modelResolution = modelResolution

        self.cache = cache

        self.latStep = cellResolution / 111
        self.lonStep = cellResolution / (111 * math.cos(math.radians(southLat)))

        scale = modelResolution / cellResolution
        self.coarseSize = int(gridSize / scale)

        self.latStepCoarse = modelResolution / 111
        self.lonStepCoarse = modelResolution / (111 * math.cos(math.radians(southLat)))

        self.coarsePoints = self._GenerateCoarseGridPoints()
        self.gridPoints = self._GenerateGridPoints()

        self.client = self._CreateClient()

    def _GenerateCoarseGridPoints(self):
        points = []

        for i in range(self.coarseSize):
            for j in range(self.coarseSize):
                latitude = self.southLat + i * self.latStepCoarse
                longitude = self.westLon + j * self.lonStepCoarse
                points.append((latitude, longitude))

        return points

    def _GenerateGridPoints(self):
        points = []

        for i in range(self.gridSize):
            for j in range(self.gridSize):
                latitude = self.southLat + i * self.latStep
                longitude = self.westLon + j * self.lonStep
                points.append((latitude, longitude))

        return points

    def _CreateClient(self):
        if self.cache:
            cacheSession = requests_cache.CachedSession('.cache', expire_after=3600)
            retrySession = retry(cacheSession, retries=8, backoff_factor=1)
            return openmeteo_requests.Client(session=retrySession)
        else:
            return openmeteo_requests.Client()


    def _Upscaledata(self, coarseData):
        scaleFactor = self.gridSize / self.coarseSize

        fineData = {}

        for key in coarseData:
            fineData[key] = zoom(coarseData[key], scaleFactor, order=1)

        return fineData

    def CreateGrid(self):
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