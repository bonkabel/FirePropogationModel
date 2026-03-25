import streamlit as st
import streamlit.components.v1 as components
import numpy as np
from geopy.geocoders import Nominatim
import requests
from Classes.Grid import Grid
from Classes.Fire_Spread import Fire_Spread
from Classes.MTTSimulation import MTTSimulation
from Classes.WeatherDataSetup import WeatherDataSetup
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.Visualization import Visualization

st.set_page_config(page_title="Fire Simulation", layout="wide")
st.title("Fire Simulation")

location_str = st.text_input("Location", value="Phoenix Arizona, US")

def geocode(location_str):
    try:
        response = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": location_str, "limit": 1},
            timeout=10
        )
        result = response.json()
        if result.get("features"):
            coords = result["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]  # lat, lon
        return None, None
    except Exception as e:
        st.error(f"Geocoding error: {str(e)}")
        return None, None

if st.button("Run Simulation"):
    with st.spinner("Running simulation, please wait..."):
        st.write("Starting simulation...")
        try:
            st.write("Geocoding location...")
            lat, lon = geocode(location_str)

            if not lat:
                st.error("Location not found.")
            else:
                gridSize = 50
                cellResolution = 2

                # Weather setup
                st.write("Setting up weather...")
                weatherSetup = WeatherDataSetup(lat, lon, gridSize, cellResolution, 10, False, True, True)
                weatherLayers = weatherSetup.CreateWeatherLayers("current")

                # Terrain setup
                st.write("Setting up terrain...")
                try:
                    terrainSetup = TerrainDataSetup(lat, lon, gridSize, cellResolution)
                    terrainLayers = terrainSetup.CreateTerrainLayers()
                    st.write("Terrain done!")
                except Exception as e:
                    import traceback

                    st.error(f"Terrain failed: {str(e)}")
                    st.code(traceback.format_exc())
                    st.stop()
                st.write("Terrain done")

                # ROS calculation
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

                # Grid
                grid = Grid(gridSize, cellResolution, weatherLayers, terrainLayers, ros, wsv, raz, ff, isi)

                # MTT Simulation
                st.write("Calculating fire spread...")
                simulation = MTTSimulation(grid, dt=3600)
                simulation.IgniteRandom(10)
                simulation.Solve()

                # Stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Mean Temperature", f"{weatherLayers['temperature'].mean():.1f}°C")
                    st.metric("Mean Humidity", f"{weatherLayers['humidity'].mean():.1f}%")
                with col2:
                    st.metric("Mean Wind Speed", f"{weatherLayers['wind_speed'].mean():.1f} km/h")
                    st.metric("Mean Precipitation", f"{weatherLayers['precipitation'].mean():.2f} mm")
                with col3:
                    st.metric("Mean ROS", f"{ros.mean():.4f} m/s")
                    st.metric("Mean ISI", f"{isi.mean():.2f}")

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

                map_html = viz.saveTimeline(streamlit=True)
                components.html(map_html, height=800, scrolling=False)

        except Exception as e:
            import traceback

            st.error(f"Simulation failed: {str(e)}")
            st.code(traceback.format_exc())









