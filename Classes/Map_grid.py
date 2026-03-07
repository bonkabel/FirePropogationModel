"""Create a grid using numpy and upload the map using matplotlib
Obtain the weather data from Open Weather Map API Keys
The spread of fire can be calculated using the map data to check what type of vegetation is 
there, rate of wind blowing.

 """

import webbrowser
import os
import math
import numpy as np
import folium
import branca.colormap as cm
import random
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


class FireGrid():
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.location = Location("London", "Canada")
        self.lat, self.lon = self.location.coordinates()

        self.north = float(self.lat) + 0.1
        self.south = float(self.lat) - 0.1
        self.east = float(self.lon) + 0.2
        self.west = float(self.lon) - 0.2

        self.lat_step = (self.north - self.south) / rows
        self.lon_step = (self.east - self.west) / cols

        # Fire affinity values (0–1)
        self.affinity = np.random.rand(rows, cols)

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

        width = f"{width/1000:.2f}"
        height = f"{height/1000:.2f}"

        print("\nMap Dimensions")
        print("----------------------")
        print(f"Width  : {width} km")
        print(f"Height : {height} km")
        print(f"Cell width  : {self.cell_width:.2f} m")
        print(f"Cell height : {self.cell_height:.2f} m")
        return width, height, self.cell_width, self.cell_height

    def show_map(self):

        # Shows  map centring with the location along with the zoom level at start
        m = folium.Map(location=[self.lat, self.lon], zoom_start=12)

        # Color gradient for grid ranging from 0 to 1
        colormap = cm.linear.YlOrRd_09.scale(0, 1)

        # Looping through each cell in the grid
        for i in range(self.rows):
            for j in range(self.cols):

                # Calculating the fire affinity value of cells in the grid
                value = self.affinity[i][j]

                # Bounds for the grid
                bounds = [
                    [(self.south) + ((i - 5) * self.lat_step),
                     (self.west) + ((j -5) * self.lon_step)],

                    [(self.south) + ((i+6)*self.lat_step),
                     (self.west) + ((j+6)*self.lon_step)]
                ]

                # Creating grid rectangle on top of the map
                folium.Rectangle(
                    bounds=bounds,
                    fill=True,
                    fill_color=colormap(value),
                    fill_opacity=0.15,
                    color=None,
                    weight=0
                ).add_to(m)

        colormap.caption = "Fire Affinity"
        colormap.add_to(m)

        # Saving the html file
        m.save("full_grid_map.html")
        # Opening it on the browser
        webbrowser.open("file://" + os.path.realpath("full_grid_map.html"))

# Values for map location
grid = FireGrid(
    rows=100,
    cols=100
)

grid.show_map()