from Classes.Grid import Grid
import numpy as np

class Simulation:
    """
    Probabilistic fire spread.
    Deterministic extinction.
    """


    def __init__(self, grid, dt):
        """

        :param grid: A Grid object containing weather and terrain data
        :param dt: Delta time. The change in time for a step in the simulation
        """
        self.grid = grid
        self.dt = dt
        self.time = 0.0

    def Step(self, steps=1):
        for step in range(steps):
            self._Calculate()
            self._Update()
            self.time += self.dt

    def _Calculate(self):
        pass



    def _Update(self):
        pass

    def Ignite(self, x, y):
        self.grid.state[x,y] = Grid.BURNING