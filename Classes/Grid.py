import numpy as np


class Grid:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.cells = np.empty((height, width), dtype=object)


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

