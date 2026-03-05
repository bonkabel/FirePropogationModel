"""This file takes the weather parameters and generate rate of spread of fire as output"""
import math
from constants import constants

class Fire_Spread():
    def __init__(self, humidity, wind, precipitation, temperature):
        self.ffmc0 = 85.0
        self.humidity = humidity
        self.wind = wind
        self.precipitation = precipitation
        self.temperature = temperature
        self.constants = constants()
        self.a = self.constants["C-1"]["a"]
        self.b = self.constants["C-1"]["b"]
        self.c = self.constants["C-1"]["c"]


    def ffmccalculation(self):
        m0 = (147.2 * (101.0 - self.ffmc0)) / (59.5 + self.ffmc0)
        if self.precipitation > 0.5:
            rf = self.precipitation - 0.5
            if m0 > 150:
                m0 = (m0 + 42.5 * rf * math.exp(-100 / (251.0 - m0)) * (1.0 - math.exp(-6.93 / rf)) + (0.0015 * (m0 - 150.0) ** 2) * math.sqrt(rf))
            elif m0 <= 150.0:
                m0 = m0 + 42.5 * rf * math.exp(-100/(251 - m0)) * (1.0 - math.exp(-6.93 / rf))
            elif m0 > 250.0:
                m0 = 250.0
        
        ed = 0.942 * (self.humidity ** (0.679)) + (11.0 * math.exp((self.humidity - 100.0) / 10.0)) + 0.18 * (21.1 - self.temperature) * (1.0 - (1.0 / math.exp(0.1150 * self.humidity)))
        
        if m0 < ed:
            ew = 0.618 * (self.humidity ** 0.753) + (10.0 * math.exp((self.humidity - 100.0) / 10.0)) + 0.18 * (21.1 - self.temperature) * (1.0 - 1.0 / math.exp(0.115 * self.humidity))
            
            if m0 <= ew:
                kl = 0.424 * (1.0 - ((100.0 - self.humidity) / 100.0) ** 1.7) + (0.0694 * math.sqrt(self.wind)) * (1.0 - ((100.0 - self.humidity) / 100.0) ** 8)
                kw = kl * (0.581 * math.exp(0.0365 * self.temperature))
                m = ew - (ew - m0) / 10.0 ** kw
            elif m0 > ew:
                m = m0
            
        elif m0 == ed:
            m = m0

        elif m0 > ed:
            kl = 0.424 * (1.0 - (self.humidity / 100.0) ** 1.7) + (0.694 * math.sqrt(self.wind)) * (1.0 - (self.humidity / 100.0) ** 8)
            kw = kl * (0.581 * math.exp(0.365 * self.temperature))
            m = ed + (m0 - ed) / 10.0 ** kw
        
        ffmc = (59.5 * (250.0 - m)) / (147.2 + m)
        if ffmc > 101.0:
            ffmc = 101.0
        elif ffmc <= 0.0:
            ffmc = 0.0

        return ffmc
    

    def isicalc(self, ffmc):
        m0 = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
        ff = 19.115 * math.exp(m0 * (-0.1386)) * (1.0 + (m0 ** 5.31) / 49300000.0)
        isi = ff * math.exp(0.05039 * self.wind)
        return isi


    def roscalc(self, isi):
        ros = self.a * (1 - (math.exp((-self.b) * isi))) ** self.c
        return ros
            
fire_spread = Fire_Spread(81.01656342, 6.36141491, 0, -9.5479798)
ffmc = fire_spread.ffmccalculation()
isi = fire_spread.isicalc(ffmc)
ros = fire_spread.roscalc(isi)
print(ffmc)
print(isi)
print(ros)