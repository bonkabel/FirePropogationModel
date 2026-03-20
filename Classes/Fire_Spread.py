"""This file takes the weather parameters and generate rate of spread of fire as output"""
import math
import numpy as np

from Classes.constants import constants


class Fire_Spread():
    def __init__(self, humidityGrid, windSpeedGrid, windDirectionGrid, precipitationGrid,
                 temperatureGrid, treesGrid, slopeMagnitudeGrid, slopeDirectionGrid):
        self.humidityGrid = humidityGrid
        self.windSpeedGrid = windSpeedGrid
        self.windDirectionGrid = windDirectionGrid
        self.precipitationGrid = precipitationGrid
        self.temperatureGrid = temperatureGrid
        self.treesGrid = treesGrid
        self.slopeMagnitudeGrid = slopeMagnitudeGrid
        self.slopeDirectionGrid = slopeDirectionGrid
        # Per-cell FFMC initial value grid (scalar default of 85.0)
        self.ffmc0 = np.full_like(humidityGrid, 85.0, dtype=float)
        self.constants = constants()

    def roscalculation(self):
        """
        Calculates the rate of spread (ROS), net effective wind speed (WSV),
        and net effective wind direction (RAZ) for each cell in a 2D grid.

        :return:
            ros: 2D array — rate of spread in metres/second
            wsv: 2D array — net effective wind speed (km/h)
            raz: 2D array — net effective wind direction (degrees)
        """
        ros = np.zeros_like(self.humidityGrid, dtype=float)
        wsv = np.zeros_like(self.humidityGrid, dtype=float)
        raz = np.zeros_like(self.humidityGrid, dtype=float)
        ff = np.zeros_like(self.humidityGrid, dtype=float)
        isi = np.zeros_like(self.humidityGrid, dtype=float)

        for i in range(len(self.humidityGrid)):
            for j in range(len(self.humidityGrid[i])):
                params = self.constants["C-2"] if self.treesGrid[i][j] else self.constants["O-1"]

                m0 = (147.2 * (101.0 - self.ffmc0[i][j])) / (59.5 + self.ffmc0[i][j])

                # Rain effect — correct chain so the m0 > 250 cap always applies
                if self.precipitationGrid[i][j] > 0.5:
                    rf = self.precipitationGrid[i][j] - 0.5
                    if m0 > 150.0:
                        m0 += (
                            42.5 * rf * math.exp(-100.0 / (251.0 - m0))
                            * (1.0 - math.exp(-6.93 / rf))
                            + 0.0015 * (m0 - 150.0) ** 2 * math.sqrt(rf)
                        )
                    else:  # m0 <= 150
                        m0 += 42.5 * rf * math.exp(-100.0 / (251.0 - m0)) * (1.0 - math.exp(-6.93 / rf))
                    if m0 > 250.0:  # cap applied after either branch
                        m0 = 250.0

                # Equilibrium drying moisture content
                ed = (
                    0.942 * (self.humidityGrid[i][j] ** 0.679)
                    + 11.0 * math.exp((self.humidityGrid[i][j] - 100.0) / 10.0)
                    + 0.18 * (21.1 - self.temperatureGrid[i][j])
                    * (1.0 - 1.0 / math.exp(0.115 * self.humidityGrid[i][j]))
                )

                # Moisture content adjustment
                if m0 < ed:
                    # Equilibrium wetting moisture content
                    ew = (
                        0.618 * (self.humidityGrid[i][j] ** 0.753)
                        + 10.0 * math.exp((self.humidityGrid[i][j] - 100.0) / 10.0)
                        + 0.18 * (21.1 - self.temperatureGrid[i][j])
                        * (1.0 - 1.0 / math.exp(0.115 * self.humidityGrid[i][j]))
                    )
                    if m0 <= ew:
                        # Wetting rate — 0.0694
                        kl = (
                            0.424 * (1.0 - ((100.0 - self.humidityGrid[i][j]) / 100.0) ** 1.7)
                            + 0.0694 * math.sqrt(self.windSpeedGrid[i][j])
                            * (1.0 - ((100.0 - self.humidityGrid[i][j]) / 100.0) ** 8)
                        )
                        kw = kl * 0.581 * math.exp(0.0365 * self.temperatureGrid[i][j])
                        m = ew - (ew - m0) / 10.0 ** kw
                    else:  # ew < m0 < ed
                        m = m0

                elif m0 == ed:
                    m = m0

                else:  # m0 > ed
                    kl = (
                        0.424 * (1.0 - (self.humidityGrid[i][j] / 100.0) ** 1.7)
                        + 0.694 * math.sqrt(self.windSpeedGrid[i][j])
                        * (1.0 - (self.humidityGrid[i][j] / 100.0) ** 8)
                    )
                    kw = kl * 0.581 * math.exp(0.0365 * self.temperatureGrid[i][j])
                    m = ed + (m0 - ed) / 10.0 ** kw

                # Update FFMC and clamp to valid range
                ffmc = (59.5 * (250.0 - m)) / (147.2 + m)
                ffmc = min(max(ffmc, 0.0), 101.0)

                # Fine fuel moisture function (ff)
                m0_new = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
                ff[i][j] = 19.115 * math.exp(-0.1386 * m0_new) * (1.0 + (m0_new ** 5.31) / 49300000.0)

                # ROS with no wind and no slope (eq 26 / ISI at zero wind)
                isi_zero = ff[i][j]
                RSZ = params['a'] * (1.0 - math.exp(-params['b'] * isi_zero)) ** params['c']

                # Slope factor (eq 39)
                slope_percent = math.tan(math.radians(self.slopeMagnitudeGrid[i][j]))
                SF = math.exp(3.533 * slope_percent ** 1.2)

                # ROS on slope with no wind (eq 40)
                RSF = RSZ * SF

                # ISF
                if self.treesGrid[i][j]:
                    # Equation 41
                    ISF = math.log(max(1.0 - (RSF / params['a']) ** (1.0 / params['c']), 1e-9)) / -params['b']
                else:
                    # Equation 43
                    CF = 0.8  # curing factor (fixed without curing grid)
                    ISF = math.log(max(1.0 - (RSF / (CF * params['a'])) ** (1.0 / params['c']), 1e-9)) / -params['b']

                # Equivalent wind speed for slope (eq 44)
                WSE = min(math.log(max(ISF / (0.208 * max(ff[i][j], 1e-9)), 1e-9)) / 0.05039, 40.0)



                # Vector combination of wind and slope
                wind_rad = math.radians((self.windDirectionGrid[i][j] + 180) % 360)
                slope_rad = math.radians(self.slopeDirectionGrid[i][j])

                Cx = self.windSpeedGrid[i][j] * math.sin(wind_rad) + WSE * math.sin(slope_rad)
                Cy = self.windSpeedGrid[i][j] * math.cos(wind_rad) + WSE * math.cos(slope_rad)

                WSV_ij = math.sqrt(Cx ** 2 + Cy ** 2)
                if WSV_ij > 0:
                    RAZ_ij = math.degrees(math.acos(max(-1.0, min(1.0, Cy / WSV_ij))))
                    if Cx < 0:
                        RAZ_ij = 360.0 - RAZ_ij
                else:
                    RAZ_ij = 0.0

                wsv[i][j] = WSV_ij
                raz[i][j] = RAZ_ij

                # Final ISI using net effective wind speed
                isi[i][j] = 0.208 * ff[i][j] * math.exp(0.05039 * WSV_ij)

                # ROS calculation with fuel-type constants
                ros[i][j] = params['a'] * (1.0 - math.exp(-params['b'] * isi[i][j])) ** params['c']

        # Convert to metres / second
        ros = ros / 60.0
        return ros, wsv, raz, ff, isi
