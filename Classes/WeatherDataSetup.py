import math

import json
from datetime import date, timedelta

import numpy as np
import openmeteo_requests
import requests_cache
import sqlite3
from retry_requests import retry
from scipy.ndimage import zoom

class WeatherDataSetup:
    """
    Creates terrain layers for the simulation grid

    Retrieves:
    - Weather data from open-meteo

    Usage: Call CreateWeatherLayers() to create 2d arrays of weather data
    """
    def __init__(self, southLat, westLon, gridSize, cellResolution, coarseResolution, cache, cacheData = False, useCachedData = False):
        """
        Creates a geographic weather grid, gets coarse weather data from open-meteo, and interpolates it to a finer resolution

        :param southLat: latitude of the bottom edge of the grid in degrees, southern boundary of the area
        :param westLon: longitude of the left edge of the grid in degrees, western boundary of the area
        :param gridSize: number of cells per side of the final fine resolution grid. Resulting grid will have the resolution (gridSize x gridSize)
        :param cellResolution: Size of each fine grid cell in kilometres. Ex: 1.0 would mean a grid cell represents 1 km x 1 km
        :param coarseResolution: Resolution of the coarse grid before interpolation. Determines what is retrieved from the API
        :param cache: Boolean value indicating whether API request caching and retry logic should be enabled
        :param cacheData: Boolean value indicating whether to cache the data or not
        :param useCachedData: Boolean value indicating whether to use cached weather data. For testing purposes.
        """

        self.southLat = southLat
        self.westLon = westLon
        self.gridSize = gridSize
        self.cellResolution = cellResolution
        self.modelResolution = coarseResolution
        self.cache = cache
        self.cacheData = cacheData
        self.useCachedData = useCachedData

        self.latStep = cellResolution / 111
        self.lonStep = cellResolution / (111 * math.cos(math.radians(southLat)))

        scale = coarseResolution / cellResolution
        self.coarseSize = int(gridSize / scale)

        self.latStepCoarse = coarseResolution / 111
        self.lonStepCoarse = coarseResolution / (111 * math.cos(math.radians(southLat)))

        self.coarsePoints = self._GenerateCoarseGridPoints()
        self.gridPoints = self._GenerateGridPoints()

        self.client = self._CreateClient()
        self.dbPath = "weather_cache.db"

        if cacheData or useCachedData:
            self._InitDB()

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

    def _InitDB(self):
        """Creates the SQLite table for weather data if it doesn't exist"""
        with sqlite3.connect(self.dbPath) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cached_at TEXT NOT NULL DEFAULT (datetime('now')),
                    data TEXT NOT NULL
                )
            """)
            conn.commit()

    def _SaveToCache(self, fineData):
        """
        Serialises fineData and stores it in the SQLite database
        :param fineData: The data to serialise
        :return:
        """
        serialisable = {
            key: [arr.tolist() for arr in daily_arrays]
            for key, daily_arrays in fineData.items()
        }

        with sqlite3.connect(self.dbPath) as conn:
            conn.execute(
                "INSERT INTO weather_cache (data) VALUES (?)",
                (json.dumps(serialisable),)
            )
            conn.commit()

    def _LoadFromCache(self):
        with sqlite3.connect(self.dbPath) as conn:
            row = conn.execute("SELECT data FROM weather_cache ORDER BY id DESC LIMIT 1").fetchone()

        if row is None:
            return None

        raw = json.loads(row[0])
        return {
            key: [np.array(arr) for arr in daily_list]
            for key, daily_list in raw.items()
        }

    def _UpscaleData(self, coarseData):
        """
        Interpolates coarse grid weather data to match the fine grid size

        Use bilinear interpolation to scale each 2D weather array

        :param coarseData: Dictionary mapping weather variable names to 2D NumPy arrays at coarse resolution.
        :return: Dictionary mapping weather variable names to 2d NumPy arrays at fine resolution
        """
        scaleFactor = self.gridSize / self.coarseSize

        fineData = {}

        for key, daily_arrays in coarseData.items():
            fineData[key] = [zoom(arr, scaleFactor, order=1) for arr in daily_arrays]

        return fineData

    def CreateWeatherLayers(self):
        """
        Fetches weather data for all coarse grid points in batches.
        Stores the results in 2D arrays.
        Interpolates them to a finer resolution

        :return: Dictionary containing fine resolution 2D NumPy arrays for reach weather variable
        """
        if self.useCachedData:
            cached = self._LoadFromCache()
            if cached is not None:
                return cached
            print("No cached data, getting from API")

        today = date.today()
        startDate = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        endDate = today.strftime("%Y-%m-%d")
        numDays = 7
        batchSize = 100

        variables = ["temperature", "humidity", "precipitation", "wind_speed", "wind_direction"]

        coarseData = {
            var: [np.zeros((self.coarseSize, self.coarseSize)) for _ in range(numDays)]
            for var in variables
        }

        for batchStart in range(0, len(self.coarsePoints), batchSize):
            batch = self.coarsePoints[batchStart:batchStart+batchSize]


            lats = [i[0] for i in batch]
            lons = [i[1] for i in batch]

            params = {
                "latitude": lats,
                "longitude": lons,
                "start_date": startDate,
                "end_date": endDate,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "wind_direction_10m"
                ]
            }

            responses = self.client.weather_api("https://archive-api.open-meteo.com/v1/era5", params=params)

            for index, response in enumerate(responses):
                i = batchStart + index
                row = i // self.coarseSize
                col = i % self.coarseSize

                hourly = response.Hourly()

                noonIndices = [12 + 24 * d for d in range(numDays)]

                allTemps = hourly.Variables(0).ValuesAsNumpy()
                allHumidity = hourly.Variables(1).ValuesAsNumpy()
                allPrecipitation = hourly.Variables(2).ValuesAsNumpy()
                allWindSpeed = hourly.Variables(3).ValuesAsNumpy()
                allWindDirection = hourly.Variables(4).ValuesAsNumpy()

                for d, ni in enumerate(noonIndices):
                    coarseData["temperature"][d][row][col] = allTemps[ni]
                    coarseData["humidity"][d][row][col] = allHumidity[ni]
                    coarseData["precipitation"][d][row][col] = allPrecipitation[ni]
                    coarseData["wind_speed"][d][row][col] = allWindSpeed[ni]
                    coarseData["wind_direction"][d][row][col] = allWindDirection[ni]

        fineData = self._UpscaleData(coarseData)

        if self.cacheData:
            self._SaveToCache(fineData)

        return fineData