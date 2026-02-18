import numpy as np


class Grid:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # weather
        self.temperature = np.zeros((self.height, self.width), dtype=np.float32)
        self.humidity = np.zeros((self.height, self.width), dtype=np.float32)
        self.rainVolume = np.zeros((self.height, self.width), dtype=np.float32)
        self.windSpeed = np.zeros((self.height, self.width), dtype=np.float32)
        self.windDirection = np.zeros((self.height, self.width), dtype=np.float32)
        self.elevation = np.zeros((self.height, self.width), dtype=np.float32)

        # terrain
        self.water = np.zeros((self.height, self.width), dtype=bool)
        self.treeCoverage = np.zeros((self.height, self.width), dtype=np.float32)

        # fire states
        self.burning = np.zeros((self.height, self.width), dtype=bool)
        self.burnt = np.zeros((self.height, self.width), dtype=bool)

        # fire probabilities
        self.pi = np.zeros((self.height, self.width), dtype=np.float32)
        self.pe = np.zeros((self.height, self.width), dtype=np.float32)


    # may not need
    def GetNeighbours(self, x, y):
        neighbours = []

        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                nx, ny = x + dx, y + dy

                if 0 <= nx < self.width and 0 <= ny < self.height:
                    neighbours.append(self.cells[ny, nx])

        return neighbours

