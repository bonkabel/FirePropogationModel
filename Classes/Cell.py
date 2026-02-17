# Likely no use for this class
class Cell:
    def __init__(self):
        self.temperature = 0.0
        self.humidity = 0.0
        self.rainVolume = 0.0
        self.windSpeed = 0.0
        self.windDirection = 0.0
        self.water = False
        self.treeCoverage = 0.0
        self.burning = False
        self.burnt = False

        self.fuel = 0.0 # Calc with tree coverage and stuff initially

        self.pi = 0.0
        self.pe = 0.0

        self._nextStep = {}

    def CalculateNext(self, neighbours, dt):
        self._nextStep.clear()

        #calculate the next step of the cell

    def Update(self):
        #update the attributes of the cell based on the next step
        for key, val in self._nextStep.items():
            setattr(self, key, val)