from flask import Flask, render_template_string, request
from geopy.geocoders import Nominatim
from Classes.Grid import Grid
from Classes.Fire_Spread import Fire_Spread
from Classes.MTTSimulation import MTTSimulation  # was Simulation
from Classes.WeatherDataSetup import WeatherDataSetup
from Classes.TerrainDataSetup import TerrainDataSetup
from Classes.Visualization import Visualization
import webbrowser
from threading import Timer

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html style="height:100%; margin:0; padding:0;">
<head>
    <title>Fire Simulation</title>
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            height: 100%;
            width: 100%;
        }
        body {
            display: flex;
            flex-direction: column;
            font-family: Arial, sans-serif;
        }
        #controls {
            padding: 10px 16px;
            background: #1a1a2e;
            color: white;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-shrink: 0;
            height: 50px;
        }
        #controls h2 {
            margin: 0;
            font-size: 16px;
            white-space: nowrap;
        }
        #controls input[type="text"] {
            padding: 6px 10px;
            border-radius: 4px;
            border: none;
            width: 280px;
        }
        #controls input[type="submit"] {
            padding: 6px 14px;
            background: #e25822;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        #loading { display: none; color: #ffa500; font-size: 14px; }
        #error { color: #ff4444; font-size: 14px; }
        #map-container {
            flex: 1;
            width: 100%;
            min-height: 0;
        }
        #map-container iframe {
            width: 100%;
            height: 100%;
            border: none;
            display: block;
        }
    </style>
</head>
<body>
    <div id="controls">
        <h2>Fire Simulation</h2>
        <form method="post" style="display:flex; align-items:center; gap:8px; margin:0;"
              onsubmit="document.getElementById('loading').style.display='block'">
            <input type="text" name="location" value="{{ location }}" placeholder="Enter location...">
            <input type="submit" value="Run Simulation">
        </form>
        <span id="loading">Running simulation, please wait...</span>
        {% if error %}<span id="error">{{ error }}</span>{% endif %}
    </div>
    <div id="map-container">
        {{ html_content|safe }}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    location_str = "Perth, Australia"
    html_content = ""
    error = ""

    if request.method == "POST":
        location_str = request.form.get("location")

        geolocator = Nominatim(user_agent="fire_sim")
        location = geolocator.geocode(location_str)

        if location:
            lat = location.latitude
            lon = location.longitude
            gridSize = 100
            cellResolution = 2

            try:
                # Weather setup
                weatherSetup = WeatherDataSetup(lat, lon, gridSize, cellResolution, 10, False, False, True)
                weatherLayers = weatherSetup.CreateWeatherLayers("current")

                # Terrain setup
                terrainSetup = TerrainDataSetup(lat, lon, gridSize, cellResolution)
                terrainLayers = terrainSetup.CreateTerrainLayers()

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
                simulation = MTTSimulation(grid, dt=3600)
                simulation.IgniteRandom(10)
                simulation.Solve()

                print(f"=== {location_str} ===")
                print(
                    f"Temperature:   min={weatherLayers['temperature'].min():.1f} mean={weatherLayers['temperature'].mean():.1f} max={weatherLayers['temperature'].max():.1f}°C")
                print(
                    f"Humidity:      min={weatherLayers['humidity'].min():.1f} mean={weatherLayers['humidity'].mean():.1f} max={weatherLayers['humidity'].max():.1f}%")
                print(
                    f"Wind speed:    min={weatherLayers['wind_speed'].min():.1f} mean={weatherLayers['wind_speed'].mean():.1f} max={weatherLayers['wind_speed'].max():.1f} km/h")
                print(
                    f"Precipitation: min={weatherLayers['precipitation'].min():.2f} mean={weatherLayers['precipitation'].mean():.2f} max={weatherLayers['precipitation'].max():.2f} mm")
                print(f"ROS:           min={ros.min():.4f} mean={ros.mean():.4f} max={ros.max():.4f} m/s")
                print(f"ISI:           min={isi.min():.2f} mean={isi.mean():.2f} max={isi.max():.2f}")

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
                html_content = viz.saveTimeline(flask=True)

            except Exception as e:
                error = f"Simulation failed: {str(e)}"
        else:
            error = "Location not found."

    return render_template_string(HTML_TEMPLATE, location=location_str, html_content=html_content, error=error)


if __name__ == "__main__":
    # Automatically open browser
    Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=False)









