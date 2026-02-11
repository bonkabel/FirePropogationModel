class Simulation:
    def __init__(self, grid, dt):
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