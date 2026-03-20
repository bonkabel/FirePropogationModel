from flask import Flask, render_template_string, request
from geopy.geocoders import Nominatim
from Classes.Grid import Grid
from Classes.Fire_Spread import Fire_Spread
from Classes.Simulation import Simulation
from Classes.WeatherDataSetup import WeatherDataSetup
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.Visualization import Visualization
import webbrowser
from threading import Timer

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Fire Simulation</title>
    <meta charset="utf-8">
</head>
<body>
    <h2>Fire Propagation Simulation</h2>
    <form method="post">
        Location: <input type="text" name="location" value="{{ location }}">
        <input type="submit" value="Run Simulation">
    </form>
    <div style="height:600px;">
        {{ html_content|safe }}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    location_str = "San Francisco, CA"
    html_content = ""
    if request.method == "POST":
        location_str = request.form.get("location")
        geolocator = Nominatim(user_agent="fire_sim")
        location = geolocator.geocode(location_str)

        if location:
            lat, lon = location.latitude, location.longitude

            # Weather & Terrain setup
            weatherSetup = WeatherDataSetup(lat, lon, 100, 2, 10, True, True, True)
            weatherLayers = weatherSetup.CreateWeatherLayers()

            terrainSetup = TerrainDataSetup(lat, lon, gridSize=100, cellResolution=2)
            terrainLayers = terrainSetup.CreateTerrainLayers()

            # Fire Spread & Simulation
            fireSpread = Fire_Spread(weatherLayers['humidity'], weatherLayers['wind_speed'], weatherLayers['precipitation'], weatherLayers['temperature'], terrainLayers['trees'])
            ros, isi = fireSpread.roscalculation()

            grid = Grid(gridSize=100, cellSize=2, weatherData=weatherLayers, terrainData=terrainLayers, rosData=ros)
            sim = Simulation(grid, dt=5, totalSteps=100)
            sim.IgniteRandom(5)
            sim.Run()

            # Visualization
            viz = Visualization(sim, weatherLayers, terrainLayers, southLat=terrainSetup.southLat, westLon=terrainSetup.westLon, northLat=terrainSetup.northLat, eastLon=terrainSetup.eastLon)
           
            html_content = viz.saveTimeline()
        else:
            html_content = "<p>Location not found</p>"

    return render_template_string(HTML_TEMPLATE, location=location_str, html_content=html_content)


if __name__ == "__main__":
    # Automatically open browser
    Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=False)

