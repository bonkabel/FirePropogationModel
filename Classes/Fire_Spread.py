"""This file takes the weather parameters and generate rate of spread of fire as output"""
import math
import numpy as np

from Classes.constants import constants


class Fire_Spread():
    def __init__(self, humidityGrid, windGrid, precipitationGrid, temperatureGrid, treesGrid):
        self.ffmc0 = 85.0
        self.humidityGrid = humidityGrid
        self.windGrid = windGrid
        self.precipitationGrid = precipitationGrid
        self.temperatureGrid = temperatureGrid
        self.treesGrid = treesGrid
        self.constants = constants()



    def roscalculation(self):
        """
        Calculates the rate of spread for a 2d grid. Each element of the grid has its own spread value
        :return: 2d array representing the rate of spread for a grid
        """
        ros = np.zeros_like(self.humidityGrid)

        for i in range(len(self.humidityGrid)):
            for j in range(len(self.humidityGrid[i])):

                params = self.constants["C-2"] if self.treesGrid[i][j] else self.constants["O-1"]

                m0 = (147.2 * (101.0 - self.ffmc0)) / (59.5 + self.ffmc0)
                if self.precipitationGrid[i][j] > 0.5:
                    rf = self.precipitationGrid[i][j] - 0.5
                    if m0 > 150:
                        m0 = (m0 + 42.5 * rf * math.exp(-100 / (251.0 - m0)) * (1.0 - math.exp(-6.93 / rf)) + (0.0015 * (m0 - 150.0) ** 2) * math.sqrt(rf))
                    elif m0 <= 150.0:
                        m0 = m0 + 42.5 * rf * math.exp(-100/(251 - m0)) * (1.0 - math.exp(-6.93 / rf))
                    elif m0 > 250.0:
                        m0 = 250.0

                ed = 0.942 * (self.humidityGrid[i][j] ** 0.679) + (11.0 * math.exp((self.humidityGrid[i][j] - 100.0) / 10.0)) + 0.18 * (21.1 - self.temperatureGrid[i][j]) * (1.0 - (1.0 / math.exp(0.1150 * self.humidityGrid[i][j])))

                if m0 < ed:
                    ew = 0.618 * (self.humidityGrid[i][j] ** 0.753) + (10.0 * math.exp((self.humidityGrid[i][j] - 100.0) / 10.0)) + 0.18 * (21.1 - self.temperatureGrid[i][j]) * (1.0 - 1.0 / math.exp(0.115 * self.humidityGrid[i][j]))

                    if m0 <= ew:
                        kl = 0.424 * (1.0 - ((100.0 - self.humidityGrid[i][j]) / 100.0) ** 1.7) + (0.0694 * math.sqrt(self.windGrid[i][j])) * (1.0 - ((100.0 - self.humidityGrid[i][j]) / 100.0) ** 8)
                        kw = kl * (0.581 * math.exp(0.0365 * self.temperatureGrid[i][j]))
                        m = ew - (ew - m0) / 10.0 ** kw
                    elif m0 > ew:
                        m = m0

                elif m0 == ed:
                    m = m0

                elif m0 > ed:
                    kl = 0.424 * (1.0 - (self.humidityGrid[i][j] / 100.0) ** 1.7) + (0.694 * math.sqrt(self.windGrid[i][j])) * (1.0 - (self.humidityGrid[i][j] / 100.0) ** 8)
                    kw = kl * (0.581 * math.exp(0.0365 * self.temperatureGrid[i][j]))
                    m = ed + (m0 - ed) / 10.0 ** kw

                ffmc = (59.5 * (250.0 - m)) / (147.2 + m)
                if ffmc > 101.0:
                    ffmc = 101.0
                elif ffmc <= 0.0:
                    ffmc = 0.0

                # ISI calculation
                m0 = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
                ff = 19.115 * math.exp(m0 * (-0.1386)) * (1.0 + (m0 ** 5.31) / 49300000.0)
                isi = ff * math.exp(0.05039 * self.windGrid[i][j])

                # ROS calculation with fuel specific constants
                ros[i][j] = params['a'] * (1 - math.exp(-params['b'] * isi)) ** params['c']

        return ros
