import requests
import streamlit as st
import streamlit.components.v1 as components

from Classes.SimulationRunner import SimulationRunner
from Classes.Visualization import Visualization


class FireSimulationApp:
    """Streamlit UI wrapper around SimulationRunner."""

    def __init__(self):
        st.set_page_config(page_title="Fire Simulation", layout="wide")

    def geocode(self, location_str):
        try:
            api_key = st.secrets.get("OPENCAGE_API_KEY")
            response = requests.get(
                "https://api.opencagedata.com/geocode/v1/json",
                params={"q": location_str, "key": api_key, "limit": 1},
                timeout=10
            )
            result = response.json()
            if result.get("results"):
                r = result["results"][0]["geometry"]
                return r["lat"], r["lng"]
            return None, None
        except Exception as e:
            st.error(f"Geocoding error: {str(e)}")
            return None, None

    def renderStats(self, stats):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Mean Temperature", f"{stats['mean_temperature']:.1f}°C")
            st.metric("Mean Humidity", f"{stats['mean_humidity']:.1f}%")
        with col2:
            st.metric("Mean Wind Speed", f"{stats['mean_wind_speed']:.1f} km/h")
            st.metric("Mean Wind Direction", f"{stats['mean_wind_direction']:.1f}°")
        with col3:
            st.metric("Mean Precipitation", f"{stats['mean_precipitation']:.2f} mm")
            st.metric("Mean ROS", f"{stats['mean_ros']:.4f} m/s")
        with col4:
            st.metric("Mean ISI", f"{stats['mean_isi']:.2f}")

    def run(self):
        st.title("Fire Simulation")
        location_str = st.text_input("Location", value="Phoenix Arizona, US")
        is_cloud = st.checkbox("Use reduced grid (faster)", value=True)
        gridSize = 50 if is_cloud else 100

        if st.button("Run Simulation"):
            with st.spinner("Running simulation, please wait..."):
                try:
                    lat, lon = self.geocode(location_str)
                    if not lat:
                        st.error("Location not found.")
                        return

                    runner = self._runSimulation(lat, lon, gridSize)  # ← changed

                    self.renderStats(runner.getStats())

                    viz = Visualization(
                        runner.simulation,
                        runner.weatherLayers,
                        runner.terrainLayers,
                        southLat=runner.terrainSetup.southLat,
                        westLon=runner.terrainSetup.westLon,
                        northLat=runner.terrainSetup.northLat,
                        eastLon=runner.terrainSetup.eastLon
                    )
                    map_html = viz.saveTimeline(streamlit=True)
                    components.html(map_html, height=800, scrolling=False)

                except Exception as e:
                    import traceback
                    st.error(f"Simulation failed: {str(e)}")
                    st.code(traceback.format_exc())

    @st.cache_data
    def _runSimulation(_self, lat, lon, gridSize):  # _self prefix tells Streamlit not to hash it
        runner = SimulationRunner(lat, lon, gridSize)
        runner.run(cacheData=False)
        return runner


