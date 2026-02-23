"""Create a grid using numpy and upload the map using matplotlib
Obtain the weather data from Open Weather Map API Keys
The spread of fire can be calculated using the map data to check what type of vegetation is 
there, rate of wind blowing.

 """

import webbrowser
import os
import numpy as np
import folium
import branca.colormap as cm
import random

class FireGrid():
    def __init__(self, south, north, west, east, rows=50, cols=50):
        self.south = south
        self.north = north
        self.west = west
        self.east = east
        self.rows = rows
        self.cols = cols

        self.lat_step = (north - south) / rows
        self.lon_step = (east - west) / cols

        # Fire affinity values (0–1)
        self.affinity = np.random.rand(rows, cols)

    def show_map(self):
        # Deciphering the center of the map
        center_lat = (self.south + self.north) / 2
        center_lon = (self.west + self.east) / 2

        # Shows  map centring with the location along with the zoom level at start
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

        # Color gradient for grid ranging from 0 to 1
        colormap = cm.linear.YlOrRd_09.scale(0, 1)

        # Looping through each cell in the grid
        for i in range(self.rows):
            for j in range(self.cols):

                # Calculating the fire affinity value of cells in the grid
                value = self.affinity[i][j]

                # Bounds for the grid
                bounds = [
                    [self.west + j*self.lon_step,
                     self.south + i*self.lat_step],

                    [self.west + (j+1)*self.lon_step,
                     self.south + (i+1)*self.lat_step]
                ]

                # Creating grid rectangle on top of the map
                folium.Rectangle(
                    bounds=bounds,
                    fill=True,
                    fill_color=colormap(value),
                    fill_opacity=0.7,
                    color=None,
                    weight=0
                ).add_to(m)

        colormap.caption = "Fire Affinity"
        colormap.add_to(m)

        # Saving the html file
        m.save("full_grid_map.html")
        print("Saved as full_grid_map.html")
        # Opening it on the browser
        webbrowser.open("file://" + os.path.realpath("fire_rectangles.html"))

# Values for map location
grid = FireGrid(
    south=23.70,
    north=23.90,
    west=90.35,
    east=90.50,
    rows=60,
    cols=60
)

grid.show_map()