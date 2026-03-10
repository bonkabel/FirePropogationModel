"""Create a grid using numpy and upload the map using matplotlib
Obtain the weather data from Open Weather Map API Keys
The spread of fire can be calculated using the map data to check what type of vegetation is 
there, rate of wind blowing.

 """

import numpy as np
import random
import folium
import webbrowser
import os
import math
import time
from WeatherDataSetup import WeatherDataSetup
from Fire_Spread import Fire_Spread
from locationaAPI import Location

#Haversine method to calculate the width and height of the map and cells
def haversine(p1, p2):
    """
    Returns distance in meters between two (lat, lon) points
    """

    R = 6371000  # Earth radius in meters

    lat1, lon1 = p1
    lat2, lon2 = p2

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

class FireGridWindROS:


    def __init__(self, rows=100, cols=100):

        self.rows = rows
        self.cols = cols

        self.location = Location("London", "Canada")
        self.lat, self.lon = self.location.coordinates()
        
        self.north = float(self.lat) + 0.1
        self.south = float(self.lat) - 0.1
        self.east = float(self.lon) + 0.2
        self.west = float(self.lon) - 0.2

        self.lat_step = (self.north - self.south)/rows
        self.lon_step = (self.east - self.west)/cols

        # fire states
        # 0 = unburned
        # 1 = burning
        # 2 = burned
        self.fire_state = np.zeros((rows, cols), dtype=int)

        self.weather_data = WeatherDataSetup(42.817816, -80.633052, 100, 2, 10, True, False, True)
        self.weatherLayers = self.weather_data.CreateWeatherLayers()
        
        self.fire_spread = Fire_Spread(81.01656342, 6.36141491, 0, -9.5479798)
        self.ros = self.fire_spread.roscalculation()
        # wind direction array (100x100)
        self.wind_dir = self.weatherLayers["wind_direction"][0]

        self.history = []

        # Calculate real map size
        self.calculate_map_size()

    
    def calculate_map_size(self):

        NW = (self.north, self.west)
        NE = (self.north, self.east)
        SW = (self.south, self.west)

        width = haversine(NW, NE)
        height = haversine(SW, NW)

        self.cell_width = width / self.cols
        self.cell_height = height / self.rows


    def ignite_random(self, n):

        for _ in range(n):
            i = random.randint(0, self.rows-1)
            j = random.randint(0, self.cols-1)
            self.fire_state[i, j] = 1


    def spread_fire(self):

        new_state = self.fire_state.copy()
        for i in range(self.rows):
            for j in range(self.cols):

                if self.fire_state[i, j] == 1:

                    # wind direction at this cell
                    
                    wind_angle = float(self.wind_dir[i, j])
                    if wind_angle == 0 or wind_angle == 90 or wind_angle == 180 or wind_angle == 270:
                        self.sleep_time = (max(self.cell_height, self.cell_width)) / 10000
                    else:
                        self.dis = (((self.cell_height**2) + (self.cell_width**2)) ** 0.5) 
                        self.sleep_time = (self.dis / self.ros) / 10000
                    
                    angle_rad = np.deg2rad(wind_angle)
                    # convert angle to grid movement
                    di = -int(round(np.cos(angle_rad)))
                    dj = int(round(np.sin(angle_rad)))
                    # move fire ros cells along wind direction
                    for step in range(1, int(self.ros) + 1):

                        ni = i + di * step
                        nj = j + dj * step

                        if 0 <= ni < self.rows and 0 <= nj < self.cols:

                            if self.fire_state[ni, nj] == 0:
                                new_state[ni, nj] = 1
                                
                                time.sleep(self.sleep_time)

                    # current cell becomes burned
                    new_state[i, j] = 2

        self.fire_state = new_state
        self.history.append(self.fire_state.copy())


    def run_simulation(self, steps=15):

        for _ in range(steps):
            self.spread_fire()


    def generate_map(self, filename="fire_wind_ros.html"):
        m = folium.Map(location=[self.lat, self.lon], zoom_start=12)

        for i in range(self.rows):
            for j in range(self.cols):

                bounds = [
                    [self.south + i*self.lat_step, self.west + j*self.lon_step],
                    [self.south + (i+1)*self.lat_step, self.west + (j+1)*self.lon_step]
                ]

                folium.Rectangle(
                    bounds=bounds,
                    color=None,
                    fill=True,
                    fill_opacity=0.7,
                    fill_color='green'
                ).add_to(m)

        states_js = "[{}]".format(",".join(
            "[" + ",".join(str(self.history[s][i, j]) for i in range(self.rows) for j in range(self.cols)) + "]"
            for s in range(len(self.history))
        ))

        animation_js = f"""
        <script>

        window.onload = function(){{

            var steps = {states_js};
            var rects = document.getElementsByClassName('leaflet-interactive');

            var t = 0;

            function animate(){{

                for(var k=0;k<rects.length;k++){{

                    var state = steps[t][k];

                    if(state==0)
                        rects[k].setAttribute('fill','green');

                    else if(state==1)
                        rects[k].setAttribute('fill','red');

                    else
                        rects[k].setAttribute('fill','black');
                }}

                t++;

                if(t < steps.length)
                    setTimeout(animate,500);
            }}

            animate();
        }};

        </script>
        """

        m.get_root().html.add_child(folium.Element(animation_js))
        m.save(filename)
        webbrowser.open("file://" + os.path.realpath(filename))
    

    # ===============================

    # Example Usage

    # ===============================

grid = FireGridWindROS(rows=100, cols=100)

# Example: replace this with your real wind_direction array


grid.ignite_random(n=7)

grid.run_simulation(steps=10)
grid.generate_map()