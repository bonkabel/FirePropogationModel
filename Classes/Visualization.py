import folium
import folium.plugins
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import math
import os
import webbrowser
from PIL import Image
from Classes.Grid import Grid


class Visualization:
    """
    Visualization class for rendering fire simulation results as a Folium map.
    Converts simulation history and environmental data layers into a html file.
    Includes toggleable map overlays.
    """


    def __init__(self, simulation, weatherlayers, terrainlayers, southLat, westLon, northLat, eastLon):
        """

        :param simulation: A completed simulation
        :param weatherlayers: Mapping of weather variable names to 2D numpy arrays
        :param terrainlayers: Mapping of terrain variable names to 2D numpy arrays
        :param southLat: Latitude of the southern boundary
        :param westLon: Longitude of the western boundary
        :param northLat: Latitude of the northern boundary
        :param eastLon: Longitude of the eastern boundary
        """
        self.sim = simulation
        self.southLat = southLat
        self.westLon = westLon
        self.northLat = northLat
        self.eastLon = eastLon

        self.temperature = weatherlayers["temperature"]
        self.precipitation = weatherlayers["precipitation"]
        self.humidity = weatherlayers["humidity"]
        self.wind_speed = weatherlayers["wind_speed"]
        self.wind_direction = weatherlayers["wind_direction"]
        self.trees = terrainlayers["trees"]

    # ------------------------------------------------------------------
    # Image helpers
    # ------------------------------------------------------------------

    def _arrayToBase64(self, rgba):
        """
        Encode a RGBA numpy array as a base64 png string
        :param rgba: Array of shape (H, W, 4) dtype uint8.
        :return: Encoded png data
        """
        img = Image.fromarray(rgba.astype(np.uint8), "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", compress_level=1)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    def _stateToImage(self, state):
        """
        Convert a grid array to an overlay image
        :param state: 2D int array of shape (rows, cols) containing cell data
        :return: Encoded png data
        """
        rgba = np.zeros((*state.shape, 4), dtype=np.uint8)
        rgba[state == Grid.BURNING] = [255, 0, 0, 180]
        rgba[state == Grid.BURNED_OUT] = [0, 0, 0, 180]
        return self._arrayToBase64(rgba)

    def _waterToImage(self, water):
        """
        Convert a 2D boolean array to an overlay
        :param water: 2D boolean array of shape (rows, cols)
        :return: Encoded png data
        """
        rgba = np.zeros((*water.shape, 4), dtype=np.uint8)
        rgba[water] = [0, 105, 148, 180]
        return self._arrayToBase64(rgba)

    def _precipitationToImage(self, precipitation):
        """
        Convert a 2d precipitation data array to an overlay
        :param precipitation: 2D float array of shape (rows, cols)
        :return: Encoded png data
        """
        if precipitation.max() > 0:
            normalized = precipitation / precipitation.max()
        else:
            normalized = precipitation
        cmap = plt.get_cmap("YlGnBu")
        rgba = (cmap(normalized) * 255).astype(np.uint8)
        rgba[precipitation == 0, 3] = 0
        return self._arrayToBase64(rgba)

    def _humidityToImage(self, humidity):
        """
        Convert a 2D humidity array to an overlay
        :param humidity: 2D float array of shape (rows, cols)
        :return: Encoded png data
        """
        humidity = np.array(humidity, dtype=float)
        normalized = (humidity - humidity.min()) / (humidity.max() - humidity.min())
        cmap = plt.get_cmap("Blues")
        rgba = (cmap(normalized) * 255).astype(np.uint8)
        return self._arrayToBase64(rgba)

    def _dataToImage(self, data, cmap="gist_earth"):
        """
        Convert an arbitrary 2D array to a colour mapped image
        :param data: 2D float array of shape (rows, cols)
        :param cmap: Name of a matplotlib coloormap
        :return: Encoded png data
        """

        cmap = plt.get_cmap(cmap)
        vmin = np.percentile(data, 2)
        vmax = np.percentile(data, 98)
        normalized = np.clip((data - vmin) / (vmax - vmin + 1e-9), 0, 1)
        rgba = (cmap(normalized) * 255).astype(np.uint8)
        return self._arrayToBase64(rgba)


    def _addDataLayer(self, m, data, cmap, label, show=False):
        """
        Add a colour mapped overlay to a Folium map
        :param m: The folium map object to add the layer to
        :param data: 2D float array to visualize
        :param cmap: matplotlib colormap name
        :param label: layer name string
        :param show: Whether the layer is visible by default
        """
        img_str = self._dataToImage(data, cmap=cmap)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{img_str}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.6,
            name=label,
            show=show
        ).add_to(m)

    def _addGridLayer(self, m, rows, cols):
        """
        Overlay a mercator correct grid of cell boundaries on a folium map
        :param m: The folium map object to add the grid to
        :param rows: The number of grid rows
        :param cols: The number of grid columns
        :return:
        """

        def lat_to_mercator(lat):
            return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

        def mercator_to_lat(y):
            return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)

        south_y = lat_to_mercator(self.southLat)
        north_y = lat_to_mercator(self.northLat)

        grid = folium.FeatureGroup(name="Grid", show=True)

        for r in range(rows + 1):
            y = south_y + (north_y - south_y) * r / rows
            lat = mercator_to_lat(y)
            folium.PolyLine(
                [[lat, self.westLon], [lat, self.eastLon]],
                weight=1, color="black", opacity=0.8,
                tooltip=str(r)
            ).add_to(grid)

        lon_step = (self.eastLon - self.westLon) / cols
        for c in range(cols + 1):
            lon = self.westLon + c * lon_step
            folium.PolyLine(
                [[self.southLat, lon], [self.northLat, lon]],
                weight=1, color="black", opacity=0.8,
                tooltip=str(rows + c)
            ).add_to(grid)

        grid.add_to(m)

    def _addWindLayer(self, m, direction, speed, sample=10):
        rows, cols = direction.shape
        lat_step = (self.northLat - self.southLat) / rows
        lon_step = (self.eastLon - self.westLon) / cols

        wind = folium.FeatureGroup(name="Wind", show=False)

        for r in range(0, rows, sample):
            for c in range(0, cols, sample):
                r_end = min(r + sample, rows)
                c_end = min(c + sample, cols)

                avg_dir = np.mean(direction[r:r_end, c:c_end])
                avg_spd = np.mean(speed[r:r_end, c:c_end])

                center_r = r + (r_end - r) / 2
                center_c = c + (c_end - c) / 2
                lat = self.southLat + center_r * lat_step
                lon = self.westLon + center_c * lon_step

                length = avg_spd * 0.3 * lat_step
                travel_bearing = np.deg2rad(avg_dir + 180)
                end_lat = lat + np.cos(travel_bearing) * length
                end_lon = lon + np.sin(travel_bearing) * length

                folium.PolyLine(
                    [[lat, lon], [end_lat, end_lon]],
                    weight=2, color="#317ff5", opacity=0.9
                ).add_to(wind)

                css_angle = avg_dir + 180
                icon = folium.DivIcon(
                    icon_size=(12, 12),
                    icon_anchor=(6, 10),
                    html=f"""
                    <div style="
                        width: 0; height: 0;
                        border-left: 6px solid transparent;
                        border-right: 6px solid transparent;
                        border-bottom: 10px solid #317ff5;
                        transform: rotate({css_angle:.1f}deg);
                        transform-origin: 50% 100%;
                    "></div>
                    """
                )
                folium.Marker(location=[end_lat, end_lon], icon=icon).add_to(wind)

        wind.add_to(m)


    def saveTimeline(self, filename="fire_simulation.html", flask=False, streamlit=False):
        """
        Builds and outputs the fire simulation timeline.

        :param filename: Output filename for standalone use
        :param flask: If True, saves to static/map.html and returns an iframe tag for Flask embedding.
                      If False, saves to filename and opens in browser.
        """
        m = folium.Map(
            location=[
                (self.southLat + self.northLat) / 2,
                (self.westLon + self.eastLon) / 2
            ],
            zoom_start=10,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri"
        )

        rows, cols = self.sim.grid.state.shape
        self._addGridLayer(m, rows, cols)
        self._addWindLayer(m, self.wind_direction, self.wind_speed, sample=10)

        water_img = self._waterToImage(self.sim.grid.water)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{water_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.8, name="Water", show=False
        ).add_to(m)

        self._addDataLayer(m, self.sim.grid.elevation, cmap="gist_earth", label="Elevation (m)")

        precip_img = self._precipitationToImage(self.sim.grid.precipitation)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{precip_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.8, name="Precipitation (mm)", show=False
        ).add_to(m)

        humidity_img = self._humidityToImage(self.sim.grid.humidity)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{humidity_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.6, name="Humidity (%)", show=False
        ).add_to(m)

        affinity_params = np.linspace(np.min(self.sim.grid.isi), np.max(self.sim.grid.isi), 10)
        fire_affinity_grid = np.digitize(self.sim.grid.isi, affinity_params, right=True)
        self._addDataLayer(m, fire_affinity_grid, cmap="hot", label="Fire Affinity", show=False)

        folium.LayerControl(collapsed=False).add_to(m)

        map_name = m.get_name()
        images = [self._stateToImage(record["state"]) for record in self.sim.history]
        images_js = str([f"data:image/png;base64,{img}" for img in images])
        times_js = str([record["time"] for record in self.sim.history])
        bounds_js = f"[[{self.southLat}, {self.westLon}], [{self.northLat}, {self.eastLon}]]"
        interval_ms = max(50, 20000 // len(images))

        slider_html = f"""
        <div style="position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
                    z-index: 1000; background: white; padding: 10px; border-radius: 8px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3); text-align: center;">
            <label><b>Step: <span id="stepLabel">0</span> / {len(images) - 1}
                   (t=<span id="timeLabel">{int(self.sim.history[0]['time']) // 3600}h {(int(self.sim.history[0]['time']) % 3600) // 60}m {int(self.sim.history[0]['time']) % 60}s</span>)
            <input type="range" min="0" max="{len(images) - 1}" value="0"
                   style="width: 300px;" id="stepSlider">
            <br>
            <button id="playBtn" style="margin-top: 5px; padding: 4px 16px;">Play</button>
        </div>
        <script>
            var images = {images_js};
            var times = {times_js};
            var bounds = {bounds_js};
            var totalSteps = {len(images)};
            var intervalMs = {interval_ms};
            var playing = false;
            var interval = null;
            var currentLayer = null;
            var layers = null;

            window.addEventListener('load', function() {{
                setTimeout(function() {{
                    var map = {map_name};
                    map.createPane('firePane');
                    map.getPane('firePane').style.zIndex = 650;
                    map.getPane('firePane').style.pointerEvents = 'none';
                    layers = images.map(function(src) {{
                        var layer = L.imageOverlay(src, bounds, {{opacity: 0, pane: 'firePane'}});
                        layer.addTo(map);
                        return layer;
                    }});
                    showStep(0);
                }}, 500);
            }});

            function showStep(step) {{
                document.getElementById('stepLabel').innerText = step;
                document.getElementById('stepSlider').value = step;
                var s = Math.round(times[step]);
                var h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60;
                document.getElementById('timeLabel').innerText = h+'h '+m+'m '+sec+'s';
                if (layers) {{
                    layers[step].setOpacity(0.6);
                    if (currentLayer && currentLayer !== layers[step]) {{
                        currentLayer.setOpacity(0);
                    }}
                    currentLayer = layers[step];
                }}
            }}

            document.getElementById('stepSlider').addEventListener('input', function() {{
                showStep(parseInt(this.value));
            }});

            document.getElementById('playBtn').addEventListener('click', function() {{
                if (playing) {{
                    clearInterval(interval);
                    playing = false;
                    this.innerText = 'Play';
                }} else {{
                    playing = true;
                    this.innerText = 'Pause';
                    var current = parseInt(document.getElementById('stepSlider').value);
                    interval = setInterval(function() {{
                        if (current >= totalSteps - 1) current = 0;
                        else current++;
                        showStep(current);
                    }}, intervalMs);
                }}
            }});
        </script>
        """

        m.get_root().html.add_child(folium.Element(slider_html))

        if flask:
            static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
            os.makedirs(static_dir, exist_ok=True)
            m.save(os.path.join(static_dir, 'map.html'))
            return '<iframe src="/static/map.html" style="width:100%; height:100%; border:none;"></iframe>'
        elif streamlit:                          # ← add this branch
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
                tmp_path = f.name
            m.save(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                html_str = f.read()
            os.unlink(tmp_path)
            return html_str
        else:
            m.save(filename)
            webbrowser.open("file://" + os.path.realpath(filename))
            print(f"Saved to {filename}")

