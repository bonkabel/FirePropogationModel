import hashlib
import math
import tempfile
import os
import re
import streamlit as st
import requests
import numpy as np
import rasterio
from concurrent.futures import ThreadPoolExecutor, as_completed
from rasterio.merge import merge
from scipy.ndimage import zoom


class TerrainDataSetup:
    """
    Creates terrain layers for the simulation grid

    Retrieves:
    - Elevation from copernicus
    - Water and tree coverage from ESA WorldCover

    Usage: Call CreateTerrainLayers() to create 2d arrays of terrain data
    """

    def __init__(self, southLat, westLon, gridSize, cellResolution, tileDirectory="tiles"):
        """
        Initializes terrain data setup

        :param southLat: Latitude of the southern edge of the simulation grid in decimal degrees
        :param westLon: Longitude of the western edge of the simulation grid in decimal degrees
        :param gridSize: Number of cells along each axis of the simulation grid
        :param cellResolution: Size of each cell in kilometers
        :param tileDirectory: Local directory to cache downloaded tiles, default is "tiles"
        """

        self.southLat = southLat
        self.westLon = westLon
        self.gridSize = gridSize
        self.cellResolution = cellResolution
        self.tileDirectory = tileDirectory


        if not os.path.isabs(self.tileDirectory):
            self.tileDirectory = os.path.join(tempfile.gettempdir(), self.tileDirectory)
        os.makedirs(self.tileDirectory, exist_ok=True)

        self.latStep = cellResolution / 111
        self.lonStep = cellResolution / (111 * math.cos(math.radians(southLat)))

        self.northLat = southLat + gridSize * self.latStep
        self.eastLon = westLon + gridSize * self.lonStep

        self.margin = 3

        self._fetchSouthLat = southLat - self.margin * self.latStep
        self._fetchWestLon = westLon - self.margin * self.lonStep
        self._fetchNorthLat = self.northLat + self.margin * self.latStep
        self._fetchEastLon = self.eastLon + self.margin * self.lonStep

    def _CacheKey(self):
        """
        Generates a hash string that uniquely identifies this grid configuration
        :return: 12 character hex string unique to this grid configuration
        """
        params = f"{self.southLat}_{self.westLon}_{self.gridSize}_{self.cellResolution}"
        return hashlib.md5(params.encode()).hexdigest()[:12]

    def _SaveArrayCache(self, data, name):
        """
        Saves a numpy array to disk

        :param data: The numpy array to save
        :param name: The name of the array
        """
        path = os.path.join(self.tileDirectory, f"{name}_{self._CacheKey()}.npy")
        np.save(path, data)

    def _LoadArrayCache(self, name):
        """
        Loads a numpy array from disk if it exists

        :param name: The name of the array
        :return: The numpy array, or None if it doesn't exist
        """
        path = os.path.join(self.tileDirectory, f"{name}_{self._CacheKey()}.npy")
        if os.path.exists(path):
            return np.load(path)
        return None

    def _GetTileNames(self, tileDegrees=1):
        """
        Determines all tile names needed to cover the bounding box

        :param tileDegrees: Size of each tile in degrees. (1 for Copernicus elevation, 3 for ESA WorldCover)
        :return: Set of tile names as strings
        """
        def snap(val):
            return int(math.floor(val / tileDegrees) * tileDegrees)

        latRange = range(snap(self.southLat), snap(self.northLat) + tileDegrees, tileDegrees)
        lonRange = range(snap(self.westLon), snap(self.eastLon) + tileDegrees, tileDegrees)

        tiles = set()
        for lat in latRange:
            for lon in lonRange:
                latPrefix = "N" if lat >= 0 else "S"
                lonPrefix = "E" if lon >= 0 else "W"
                tiles.add(f"{latPrefix}{abs(lat):02d}{lonPrefix}{abs(lon):03d}")

        return tiles

    def _DownloadTile(self, tileName, baseUrl, filenameTemplate):
        """
        Downloads a tile if it's not already stored locally

        :param tileName: Tile string identifier
        :param baseUrl: Base URL of the tile source
        :param filenameTemplate: Filename template with {tile} placeholder
        :return: Local file path to the downloaded tile
        """
        filename = filenameTemplate.format(tile=tileName)
        filepath = os.path.join(self.tileDirectory, filename)

        if os.path.exists(filepath):
            return filepath

        url = f"{baseUrl}/{filename}"

        print(f"Downloading worldcover tile: {filename}")
        response = requests.get(url)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        return filepath

    def _DownloadCopernicusTile(self, tileName):
        """
        Builds the correct Copernicus GLO-30 URL and downloads the tile.

        :param tileName: Tile string identifier
        :return: Local file path to the downloaded tile
        """
        match = re.match(r'([NS]\d+)([EW]\d+)', tileName)
        if not match:
            raise ValueError(f"Cannot parse tile name: {tileName}")

        lat_part = match.group(1)
        lon_part = match.group(2)

        folder = f"Copernicus_DSM_COG_10_{lat_part}_00_{lon_part}_00_DEM"
        filename = f"{folder}.tif"
        url = f"https://copernicus-dem-30m.s3.amazonaws.com/{folder}/{filename}"

        filepath = os.path.join(self.tileDirectory, filename)

        if os.path.exists(filepath):
            return filepath

        print(f"Downloading elevation tile: {filename}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return filepath

    def _FetchElevation(self):
        """
        Downloads and processes elevation for the bounding box.
        Resampled to match the simulation grid dimensions.

        :return: 2D numpy array of elevation values in meters, shape (gridSize, gridSize)
        """
        tileNames = self._GetTileNames(1)
        paths = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(self._DownloadCopernicusTile, tile): tile for tile in tileNames}
            for future in as_completed(futures):
                try:
                    paths.append(future.result())
                    st.write("elevation tile downloaded")
                except requests.HTTPError:
                    print(f"Elevation tile {futures[future]} not found, skipping.")

        if not paths:
            raise RuntimeError("No elevation tiles were successfully downloaded")

        st.write("elevation tiles downloaded")

        datasets = []
        fetchSize = self.gridSize + self.margin * 2
        pixel_width = (self._fetchEastLon - self._fetchWestLon) / fetchSize
        pixel_height = (self._fetchNorthLat - self._fetchSouthLat) / fetchSize
        try:
            for p in paths:
                datasets.append(rasterio.open(p))

            mosaic, transform = merge(
                datasets,
                bounds=(
                    self._fetchWestLon,
                    self._fetchSouthLat,
                    self._fetchEastLon,
                    self._fetchNorthLat
                ),
                res=(pixel_width, pixel_height),
            )
        finally:
            for ds in datasets:
                ds.close()

        st.write("merged elevation tiles")

        cropped = mosaic[0].astype(np.float32)
        cropped[cropped < -1000] = np.nan

        fetchSize = self.gridSize + self.margin * 2
        scaleY = fetchSize / cropped.shape[0]
        scaleX = fetchSize / cropped.shape[1]

        return zoom(cropped, (scaleY, scaleX), order=1)

    def _FetchLandCover(self):
        """
        Downloads and processes landcover data for the bounding box.
        Resampled to match the simulation grid dimensions.

        :return: Tuple of (water, trees), each a boolean numpy array of shape (gridSize, gridSize). True indicates the presence of that cover type
        """
        tileNames = self._GetTileNames(3)
        paths = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(
                    self._DownloadTile,
                    tile,
                    "https://esa-worldcover.s3.amazonaws.com/v200/2021/map",
                    "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
                ): tile for tile in tileNames
            }
            for future in as_completed(futures):
                try:
                    paths.append(future.result())
                except requests.HTTPError:
                    print(f"LandCover tile {futures[future]} not found, skipping.")

        if not paths:
            raise RuntimeError("No landcover tiles were successfully downloaded")

        st.write("landcover tiles downloaded")

        datasets = []
        fetchSize = self.gridSize + self.margin * 2
        pixel_width = (self._fetchEastLon - self._fetchWestLon) / fetchSize
        pixel_height = (self._fetchNorthLat - self._fetchSouthLat) / fetchSize
        try:
            for p in paths:
                datasets.append(rasterio.open(p))

            mosaic, transform = merge(
                datasets,
                bounds=(
                    self._fetchWestLon,
                    self._fetchSouthLat,
                    self._fetchEastLon,
                    self._fetchNorthLat
                ),
                res=(pixel_width, pixel_height),
            )
        finally:
            for ds in datasets:
                ds.close()

        st.write("merged elevation tiles")


        cropped = mosaic[0]

        fetchSize = self.gridSize + self.margin * 2
        scaleY = fetchSize / cropped.shape[0]
        scaleX = fetchSize / cropped.shape[1]

        resampled = zoom(cropped, (scaleY, scaleX), order=0)

        WATER_CLASS = 80
        TREE_CLASS = 10

        return resampled == WATER_CLASS, resampled == TREE_CLASS

    def _ComputeSlope(self, elevation):
        """
        Computes slope from elevation data

        :param elevation: The elevation data to compute slope with
        :return: The magnitude of the slope, and the direction of the slope. In degrees.
        """
        cellSizeMeters = self.cellResolution * 1000
        m = self.margin

        dzdx = np.gradient(elevation, axis=1) / cellSizeMeters
        dzdy = np.gradient(elevation, axis=0) / cellSizeMeters

        dzdx = dzdx[m:-m, m:-m]
        dzdy = dzdy[m:-m, m:-m]

        magnitudeRadians = np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))
        magnitudeDegrees = np.degrees(magnitudeRadians)

        directionRadians = np.arctan2(dzdx, -dzdy)
        directionDegrees = np.degrees(directionRadians)

        return magnitudeDegrees, directionDegrees

    def CreateTerrainLayers(self):
        """
        Fetches and computes all terrain layers for the simulation grid.
        Loads from array cache if available, otherwise fetches from source and saves to cache.

        :return: Dictionary containing:
            - elevation: 2D float array of elevation in meters
            - slope_magnitude: 2D float array of slope steepness in degrees
            - slope_direction: 2D float array of slope direction in degrees, clockwise from north
            - water: 2D boolean array, True where water is present
            - trees: 2D boolean array, True where tree cover is present
        """
        elevation = self._LoadArrayCache("elevation")
        slopeMagnitude = self._LoadArrayCache("slope_magnitude")
        slopeDirection = self._LoadArrayCache("slope_direction")
        water = self._LoadArrayCache("water")
        trees = self._LoadArrayCache("trees")

        if all(v is not None for v in [elevation, slopeMagnitude, slopeDirection, water, trees]):
            print("Loaded terrain from array cache")
            return {
                "elevation": elevation,
                "slope_magnitude": slopeMagnitude,
                "slope_direction": slopeDirection,
                "water": water,
                "trees": trees
            }

        m = self.margin
        elevation = self._FetchElevation()
        slopeMagnitude, slopeDirection = self._ComputeSlope(elevation)
        elevation = elevation[m:-m, m:-m]
        water, trees = self._FetchLandCover()
        water = water[m:-m, m:-m]
        trees = trees[m:-m, m:-m]

        self._SaveArrayCache(elevation, "elevation")
        self._SaveArrayCache(slopeMagnitude, "slope_magnitude")
        self._SaveArrayCache(slopeDirection, "slope_direction")
        self._SaveArrayCache(water, "water")
        self._SaveArrayCache(trees, "trees")

        return {
            "elevation": elevation,
            "slope_magnitude": slopeMagnitude,
            "slope_direction": slopeDirection,
            "water": water,
            "trees": trees
        }