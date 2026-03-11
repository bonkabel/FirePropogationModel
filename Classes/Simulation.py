import math
import random

from Classes.Grid import Grid
import numpy as np

class Simulation:
    """
    Probabilistic fire spread.
    Deterministic extinction.
    """

    def __init__(self, grid, dt, totalSteps=25):
        """
        :param grid: A Grid object containing weather and terrain data
        :param dt: Delta time. The change in time for a step in the simulation
        :param totalSteps: The total number of step the simulation runs
        """
        self.grid = grid
        self.dt = dt
        self.time = 0.0
        self.totalSteps = totalSteps

        self.history = []

    def Run(self):
        """
        Runs the simulation for the number of steps specified in totalSteps.
        """
        for step in range(self.totalSteps):
            self.Step()

    def Step(self, steps=1):
        """
        Performs one step of the simulation.
        Records the state in history
        :param steps: The number of steps to perform
        """
        for step in range(steps):
            self._Calculate()
            self._Update()
            self.time += self.dt
            self.history.append({
                'time': self.time,
                'state': self.grid.state.copy()
            })

    def _Calculate(self):
        """
        Determines which cells ignite or extinguish in the next update
        Burning cells are checked for extinction based on their burn timer
        Results are stored in _pendingIgnitions and _pendingExtinctions
        """
        self._pendingIgnitions = set()
        self._pendingExtinctions = set()

        for x in range(self.grid.gridSize):
            for y in range(self.grid.gridSize):

                if self.grid.state[x][y] == Grid.BURNING:

                    if self.grid.fireTimer[x][y] >= self._burnoutTime(x, y) - self.dt:
                        self._pendingExtinctions.add((x, y))
                        continue

                    for nx, ny, distance in self._getNeighbours(x, y):
                        if self.grid.state[nx][ny] == Grid.UNBURNED:
                            p = self._spreadProbability(x, y, nx, ny, distance)
                            if random.random() < p:
                                self._pendingIgnitions.add((nx, ny))

    def _Update(self):
        """
        Applies the pending ignitions and extinction calculated in _Calculate.
        Also advanced the fire timer for all currently burning cells
        """
        burningMask = self.grid.state == Grid.BURNING
        self.grid.fireTimer[burningMask] += self.dt

        for x, y in self._pendingIgnitions:
            self.Ignite(x, y)

        for x, y in self._pendingExtinctions:
            self.grid.state[x][y] = Grid.BURNED_OUT

    def _burnoutTime(self, x, y):
        """
        Return the time in seconds a cell burns before extinguishing.
        Trees burn significantly longer than grass.
        :param x: The x coordinate of the cell
        :param y: The y coordinate of the cell
        :return: The time the cell will burn for
        """
        if self.grid.trees[x][y]:
            return 600  # trees burn longer
        return 120       # grass burns out faster

    def _getNeighbours(self, x, y):
        """
        Get the neighbours of (x,y). With distance, weighting diagonals
        :param x: The x coordinate of the cell on the grid
        :param y: The y coordinate of the cell on the grid
        :return: Coordinates of neighbouring cells and their distance in the form (x, y, distance)
        """
        neighbours = []

        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid.gridSize and 0 <= ny < self.grid.gridSize:
                distance = math.sqrt(dx**2 + dy**2)
                neighbours.append((nx, ny, distance))

        return neighbours

    def _spreadProbability(self, x, y, nx, ny, distance):
        """
        Calculates the probability of a fire spreading from (x, y) to (nx, ny).
        Combines a base rate of spread probability with wind and slope alignment.
        Returns 0.0 for water cells. Clamped to [0.0, 1.0]
        :param x: The x coordinate of the cell
        :param y: The y coordinate of the cell
        :param nx: The x coordinate of the neighbouring cell
        :param ny: The y coordinate of the neighbouring cell
        :param distance: The distance to the neighbouring cell
        :return: The probability of fire spreading from (x, y) to (nx, ny)
        """
        # Water
        if self.grid.water[nx][ny]:
            return 0.0

        # Base probability from destination cell's ROS
        base_p = min((self.grid.ros[nx][ny] * self.dt) / (self.grid.cellSize * distance), 1.0)

        # Wind alignment
        spreadDx, spreadDy = nx - x, ny - y
        windRadians = math.radians(self.grid.windDirection[x][y])
        windDx = math.sin(windRadians)
        windDy = math.cos(windRadians)
        windDot = (spreadDx * windDx + spreadDy * windDy) / distance
        windFactor = 0.2 + (0.8 * (1.0 + windDot))

        # Slope alignment
        slopeRadians = math.radians(self.grid.slopeDirection[x][y])
        slopeDx = math.sin(slopeRadians)
        slopeDy = math.cos(slopeRadians)
        slopeDot = (spreadDx * slopeDx + spreadDy * slopeDy) / distance
        MAX_SLOPE = 45.0
        slopeFactor = max(0.1, 1.0 + (slopeDot * self.grid.slopeMagnitude[x][y] / MAX_SLOPE))

        p = base_p * windFactor * slopeFactor
        return min(p, 1.0)

    def Ignite(self, x, y):
        """
        Ignites a cell
        :param x: The x coordinate of the cell
        :param y: The y coordinate of the cell
        """
        self.grid.state[x, y] = Grid.BURNING

    def IgniteRandom(self, numberToIgnite):
        """
        Ignites a certain number of cells randomly. Ignores cells with water
        :param numberToIgnite: The number of cells to ignite
        """
        nonWaterCells = [(x, y) for x in range(self.grid.gridSize)
                                 for y in range(self.grid.gridSize)
                                 if not self.grid.water[x][y]]

        if len(nonWaterCells) < numberToIgnite:
            raise ValueError(f"Not enough non-water cells to ignite {numberToIgnite} cells")

        cells = random.sample(nonWaterCells, numberToIgnite)
        for x, y in cells:
            self.Ignite(x, y)