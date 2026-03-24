

import streamlit as st
from geopy.geocoders import Nominatim
from Classes.MTTSimulation import MTTSimulation
from Classes.Grid import Grid
from Classes.Fire_Spread import Fire_Spread
from Classes.Simulation import Simulation
from Classes.WeatherDataSetup import WeatherDataSetup
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.Visualization import Visualization
import time

st.set_page_config(page_title="Fire Simulation", layout="wide")
st.title("🔥 Fire Propagation Simulation")


# CACHED FUNCTIONS

@st.cache_data
def geocode_location(location_str):
    geolocator = Nominatim(user_agent="fire_sim")
    return geolocator.geocode(location_str)


@st.cache_data(show_spinner=False)
def run_simulation(lat, lon):
    # Weather & Terrain setup
    weatherSetup = WeatherDataSetup(lat, lon, 100, 2, 10, True, True, True)
    weatherLayers = weatherSetup.CreateWeatherLayers()

    terrainSetup = TerrainDataSetup(lat, lon, gridSize=100, cellResolution=2)
    terrainLayers = terrainSetup.CreateTerrainLayers()

    # Fire Spread
    fireSpread = Fire_Spread(
                    weatherLayers['humidity'],
                    weatherLayers['wind_speed'],
                    weatherLayers['wind_direction'],
                    weatherLayers['precipitation'],
                    weatherLayers['temperature'],
                    terrainLayers['trees'],
                    terrainLayers['slope_magnitude'],
                    terrainLayers['slope_direction']
                )

    ros, wsv, raz, ff, isi = fireSpread.roscalculation()

    # Grid + Simulation
    grid = Grid(
        gridSize=100,
        cellSize=2,
        weatherData=weatherLayers,
        terrainData=terrainLayers,
        rosData=ros,
        wsvData=wsv,
        razData=raz,
        ffData=ff,
        isiData=isi
    )

    # MTT Simulation
    simulation = MTTSimulation(grid, dt=3600)
    simulation.IgniteRandom(10)
    simulation.Solve()

    # Visualization
    viz = Visualization(
        simulation,
        weatherLayers,
        terrainLayers,
        southLat=terrainSetup.southLat,
        westLon=terrainSetup.westLon,
        northLat=terrainSetup.northLat,
        eastLon=terrainSetup.eastLon
    )

    return viz.saveTimeline()


# UI INPUT

location_str = st.text_input("Enter Location", "San Francisco, CA")

if st.button("Run Simulation"):

    progress = st.progress(0)
    status = st.empty()

    # Step 1: Geocoding
    status.text("📍 Finding location...")
    progress.progress(10)

    location = geocode_location(location_str)

    if location:
        lat, lon = location.latitude, location.longitude

        # Smooth progress animation helper
        def smooth_progress(start, end, text):
            status.text(text)
            for i in range(start, end):
                progress.progress(i)
                time.sleep(0.01)  # small delay for smooth animation

        # Step 2
        smooth_progress(10, 25, "🌦️ Preparing weather data...")

        # Step 3
        smooth_progress(25, 40, "🌲 Preparing terrain data...")

        # Step 4 (heavy computation)
        status.text("🔥 Running fire simulation...")

        with st.spinner("Running heavy computation..."):
            html_content = run_simulation(lat, lon)

        progress.progress(85)

        # Step 5
        smooth_progress(85, 100, "🗺️ Rendering visualization...")

        status.text("✅ Done!")

        # Output
        st.components.v1.html(html_content, height=600, scrolling=True)

    else:
        st.error("Location not found")






