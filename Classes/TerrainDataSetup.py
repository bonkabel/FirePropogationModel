import math
import time
import os
import requests
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds
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

        os.makedirs(self.tileDirectory, exist_ok=True)

        self.latStep = cellResolution / 111
        self.lonStep = cellResolution / (111 * math.cos(math.radians(southLat)))

        self.northLat = southLat + gridSize * self.latStep
        self.eastLon = westLon + gridSize * self.lonStep

    def _GetTileNames(self, tileDegrees=1):
        """
        Determines all tile named needed to cover the bounding box

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

        import re
        match = re.match(r'([NS]\d+)([EW]\d+)', tileName)
        if not match:
            raise ValueError(f"Cannot parse tile name: {tileName}")

        lat_part = match.group(1)  # e.g. "N44"
        lon_part = match.group(2)  # e.g. "W080"

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
        datasets = []

        for tile in tileNames:
            try:
                path = self._DownloadCopernicusTile(tile)
                datasets.append(rasterio.open(path))
            except requests.HTTPError:
                print(f"Elevation tile {tile} not found, skipping.")
                continue

        if not datasets:
            raise RuntimeError("No tiles were successfully downloaded")

        mosaic, transform = merge(datasets)

        for ds in datasets:
            ds.close()

        bounds = (self.westLon, self.southLat, self.eastLon, self.northLat)
        window = from_bounds(*bounds, transform=transform)
        window = window.round_offsets().round_lengths()

        cropped = mosaic[0, int(window.row_off):int(window.row_off + window.height), int(window.col_off):int(window.col_off + window.width)]

        # Replace values with no data with NaN
        cropped = cropped.astype(np.float32)
        cropped[cropped < -1000] = np.nan

        # Resample
        scaleY = self.gridSize / cropped.shape[0]
        scaleX = self.gridSize / cropped.shape[1]

        resampled = zoom(cropped, (scaleY, scaleX), order=1)

        return resampled


    def _FetchLandCover(self):
        """
        Downloads and processes landcover data for the bounding box.
        Resampled to match the simulation grid dimensions.

        :return: Tuple of (water, trees), each a boolean numpy array of shape (gridSize, gridSize). True indicates the presence of that cover type
        """

        tileNames = self._GetTileNames(3)
        datasets = []

        for tile in tileNames:
            try:
                path = self._DownloadTile(
                    tile,
                    "https://esa-worldcover.s3.amazonaws.com/v200/2021/map",
                    "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
                )
                datasets.append(rasterio.open(path))
            except requests.HTTPError:
                print(f"LandCover tile {tile} not found, skipping.")
                continue

        if not datasets:
            raise RuntimeError("No tiles were successfully downloaded")

        mosaic, transform = merge(datasets)

        for ds in datasets:
            ds.close()

        bounds = (self.westLon, self.southLat, self.eastLon, self.northLat)
        window = from_bounds(*bounds, transform=transform)
        window = window.round_offsets().round_lengths()

        cropped = mosaic[0, int(window.row_off):int(window.row_off + window.height), int(window.col_off):int(window.col_off + window.width)]

        scaleY = self.gridSize / cropped.shape[0]
        scaleX = self.gridSize / cropped.shape[1]

        resampled = zoom(cropped, (scaleY, scaleX), order =0)

        WATER_CLASS = 80
        TREE_CLASS = 10

        waterMask = resampled == WATER_CLASS
        treeMask = resampled == TREE_CLASS

        return waterMask, treeMask

    def _ComputeSlope(self, elevation):
        """
        Computes slope from elevation data

        :param elevation: The elevation data to computer slope with
        :return: The magnitude of the slope, and the direction of the slope. In degrees.
        """

        cellSizeMeters = self.cellResolution * 1000

        dzdx = np.gradient(elevation, axis=1) / cellSizeMeters
        dzdy = np.gradient(elevation, axis=0) / cellSizeMeters

        # slope magnitude
        magnitudeRadians = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
        magnitudeDegrees = np.degrees(magnitudeRadians)

        # slope direction
        directionRadians = np.arctan2(dzdx, -dzdy)
        directionDegrees = np.degrees(directionRadians)

        return magnitudeDegrees, directionDegrees

    def CreateTerrainLayers(self):
        """
        Fetches and computes all terrain layers for the simulation grid

        :return: Dictionary containing:
            - elevation: 2D float array of elevation in meters
            - slop_magnitude: 2D float array of slope steepness in degrees
            - slope_direction: 2D float array of slope direction in degrees, clockwise from north
            - water: 2D boolean array, True where water is present
            - trees: 2D boolean array, True where tree cover is present
        """

        elevation = self._FetchElevation()
        slopeMagnitude, slopeDirection = self._ComputeSlope(elevation)
        water, trees = self._FetchLandCover()

        return {
            "elevation": elevation,
            "slope_magnitude": slopeMagnitude,
            "slope_direction": slopeDirection,
            "water": water,
            "trees": trees
        }




