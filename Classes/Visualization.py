import folium
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image
from Classes.Grid import Grid


class Visualization:

    def __init__(self, simulation, southLat, westLon, northLat, eastLon):
        self.sim = simulation
        self.southLat = southLat
        self.westLon = westLon
        self.northLat = northLat
        self.eastLon = eastLon

    def _arrayToBase64(self, rgba):
        img = Image.fromarray(rgba, "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    def _stateToImage(self, state):

        rgba = np.zeros((*state.shape, 4), dtype=np.uint8)

        rgba[state == Grid.BURNING] = [255, 0, 0, 180]
        rgba[state == Grid.BURNED_OUT] = [0, 0, 0, 180]

        return self._arrayToBase64(rgba)

    def _waterToImage(self, water):

        rgba = np.zeros((*water.shape, 4), dtype=np.uint8)
        rgba[water] = [0, 105, 148, 180]

        return self._arrayToBase64(rgba)

    def _precipitationToImage(self, precipitation):

        if precipitation.max() > 0:
            normalized = precipitation / precipitation.max()
        else:
            normalized = precipitation

        cmap = plt.get_cmap("YlGnBu")
        rgba = (cmap(normalized) * 255).astype(np.uint8)

        rgba[precipitation == 0, 3] = 0

        return self._arrayToBase64(rgba)

    def _humidityToImage(self, humidity):

        humidity = np.array(humidity, dtype=float)

        normalized = (humidity - humidity.min()) / (humidity.max() - humidity.min())

        cmap = plt.get_cmap("Blues")
        rgba = (cmap(normalized) * 255).astype(np.uint8)

        return self._arrayToBase64(rgba)

    def _dataToImage(self, data, cmap="Blues"):

        cmap = plt.get_cmap(cmap)

        normalized = (data - data.min()) / (data.max() - data.min())

        rgba = (cmap(normalized) * 255).astype(np.uint8)

        return self._arrayToBase64(rgba)

    def _addDataLayer(self, m, data, cmap, label, show=False):

        img_str = self._dataToImage(data, cmap=cmap)

        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{img_str}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.6,
            name=label,
            show=show
        ).add_to(m)

    def saveTimeline(self, filename="fire_simulation.html"):

        m = folium.Map(
            location=[
                (self.southLat + self.northLat) / 2,
                (self.westLon + self.eastLon) / 2
            ],
            zoom_start=10
        )

        water_img = self._waterToImage(self.sim.grid.water)

        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{water_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.8,
            name="Water",
            show=False
        ).add_to(m)

        self._addDataLayer(
            m,
            self.sim.grid.elevation,
            cmap="terrain",
            label="Elevation (m)"
        )

        precip_img = self._precipitationToImage(self.sim.grid.precipitation)

        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{precip_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.8,
            name="Precipitation (mm)",
            show=False
        ).add_to(m)

        humidity_img = self._humidityToImage(self.sim.grid.humidity)

        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{humidity_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.6,
            name="Humidity (%)",
            show=False
        ).add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)

        images = []
        for record in self.sim.history:
            images.append(self._stateToImage(record["state"]))

        images_js = str([f"data:image/png;base64,{img}" for img in images])
        times_js = str([record["time"] for record in self.sim.history])

        bounds_js = f"[[{self.southLat}, {self.westLon}], [{self.northLat}, {self.eastLon}]]"

        interval_ms = max(50, 20000 // len(images))

        slider_html = f"""
        <div style="position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
                    z-index: 1000; background: white; padding: 10px; border-radius: 8px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3); text-align: center;">
            <label><b>Step: <span id="stepLabel">0</span> / {len(images) - 1}
                   (t=<span id="timeLabel">{self.sim.history[0]['time']:.1f}</span>)</b></label><br>
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
            var map = null;

            window.addEventListener('load', function() {{

                setTimeout(function() {{

                    for (var key in window) {{
                        try {{
                            if (window[key] &&
                                window[key]._leaflet_id !== undefined &&
                                window[key].addLayer) {{
                                map = window[key];
                                break;
                            }}
                        }} catch(e) {{}}
                    }}

                    layers = images.map(function(src) {{
                        var layer = L.imageOverlay(src, bounds, {{opacity: 0}});
                        layer.addTo(map);
                        return layer;
                    }});

                    showStep(0);

                }}, 500);

            }});

            function showStep(step) {{

                document.getElementById('stepLabel').innerText = step;
                document.getElementById('stepSlider').value = step;

                document.getElementById('timeLabel').innerText =
                    times[step].toFixed(1);

                if (map && layers) {{

                    layers[step].setOpacity(0.6);

                    if (currentLayer && currentLayer !== layers[step]) {{
                        currentLayer.setOpacity(0);
                    }}

                    currentLayer = layers[step];

                }}
            }}

            document.getElementById('stepSlider')
                .addEventListener('input', function() {{

                    showStep(parseInt(this.value));

                }});

            document.getElementById('playBtn')
                .addEventListener('click', function() {{

                    if (playing) {{

                        clearInterval(interval);
                        playing = false;
                        this.innerText = 'Play';

                    }} else {{

                        playing = true;
                        this.innerText = 'Pause';

                        var current =
                            parseInt(document.getElementById('stepSlider').value);

                        interval = setInterval(function() {{

                            if (current >= totalSteps - 1)
                                current = 0;
                            else
                                current++;

                            showStep(current);

                        }}, intervalMs);

                    }}

                }});

        </script>
        """

        m.get_root().html.add_child(folium.Element(slider_html))

        m.save(filename)

        print("Saved to", filename)