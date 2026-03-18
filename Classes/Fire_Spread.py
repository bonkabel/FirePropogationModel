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
        self.ffmc0 = np.full_like(humidityGrid, 85.0, dtype=float)
        self.constants = constants()

    def roscalculation(self):
        """
        Calculates the rate of spread (ROS) and ISI for each cell in a 2D grid
        :return: ros (2D array), isi (2D array)
        """
        ros = np.zeros_like(self.humidityGrid, dtype=float)
        isi_grid = np.zeros_like(self.humidityGrid, dtype=float)

        for i in range(len(self.humidityGrid)):
            for j in range(len(self.humidityGrid[i])):
                params = self.constants["C-2"] if self.treesGrid[i][j] else self.constants["O-1"]

                # FFMC adjustment
                m0 = (147.2 * (101.0 - self.ffmc0[i][j])) / (59.5 + self.ffmc0[i][j])

                # Rain effect
                if self.precipitationGrid[i][j] > 0.5:
                    rf = self.precipitationGrid[i][j] - 0.5
                    if m0 > 150:
                        m0 += 42.5 * rf * math.exp(-100 / (251.0 - m0)) * (1 - math.exp(-6.93 / rf)) \
                            + 0.0015 * (m0 - 150) ** 2 * math.sqrt(rf)
                    elif m0 <= 150:
                        m0 += 42.5 * rf * math.exp(-100 / (251.0 - m0)) * (1 - math.exp(-6.93 / rf))
                    if m0 > 250:
                        m0 = 250.0

                # Equilibrium moisture contents
                ed = 0.942 * (self.humidityGrid[i][j] ** 0.679) + 11.0 * math.exp((self.humidityGrid[i][j] - 100) / 10) \
                    + 0.18 * (21.1 - self.temperatureGrid[i][j]) * (1 - 1 / math.exp(0.115 * self.humidityGrid[i][j]))
                ew = 0.618 * (self.humidityGrid[i][j] ** 0.753) + 10.0 * math.exp((self.humidityGrid[i][j] - 100) / 10) \
                    + 0.18 * (21.1 - self.temperatureGrid[i][j]) * (1 - 1 / math.exp(0.115 * self.humidityGrid[i][j]))

                # Moisture content adjustment
                if m0 < ed:
                    if m0 <= ew:
                        kl = 0.424 * (1 - ((100 - self.humidityGrid[i][j]) / 100) ** 1.7) \
                            + 0.0694 * math.sqrt(self.windGrid[i][j]) * (1 - ((100 - self.humidityGrid[i][j]) / 100) ** 8)
                        kw = kl * 0.581 * math.exp(0.0365 * self.temperatureGrid[i][j])
                        m = ew - (ew - m0) / 10 ** kw
                    else:
                        m = m0
                elif m0 == ed:
                    m = m0
                else:  # m0 > ed
                    kl = 0.424 * (1 - (self.humidityGrid[i][j] / 100) ** 1.7) + 0.694 * math.sqrt(self.windGrid[i][j]) \
                        * (1 - (self.humidityGrid[i][j] / 100) ** 8)
                    kw = kl * 0.581 * math.exp(0.0365 * self.temperatureGrid[i][j])
                    m = ed + (m0 - ed) / 10 ** kw

                # Update FFMC
                ffmc = (59.5 * (250 - m)) / (147.2 + m)
                ffmc = min(max(ffmc, 0.0), 101.0)

                # ISI calculation (grid-based)
                m0_new = 147.2 * (101 - ffmc) / (59.5 + ffmc)
                ff = 19.115 * math.exp(-0.1386 * m0_new) * (1 + (m0_new ** 5.31) / 49300000.0)
                isi = ff * math.exp(0.05039 * self.windGrid[i][j])

                isi_grid[i][j] = isi

                # ROS calculation with fuel constants
                ros[i][j] = params['a'] * (1 - math.exp(-params['b'] * isi)) ** params['c']

        return ros, isi_grid