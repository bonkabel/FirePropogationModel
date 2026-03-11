import folium
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import base64
from Classes.Grid import Grid
import math


class Visualization:
    def __init__(self, simulation, southLat, westLon, northLat, eastLon):
        self.sim = simulation
        self.southLat = southLat
        self.westLon = westLon
        self.northLat = northLat
        self.eastLon = eastLon

    def _stateToImage(self, state):
        """Convert state array to base64 PNG with transparent background"""
        rgba = np.zeros((*state.shape, 4), dtype=np.uint8)
        rgba[state == Grid.BURNING] = [255, 0, 0, 180]
        rgba[state == Grid.BURNED_OUT] = [0, 0, 0, 180]

        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(rgba, interpolation='nearest')
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        plt.close()
        return img_str

    def _waterToImage(self, water):
        """Convert water boolean array to base64 PNG with transparent non-water cells"""
        rgba = np.zeros((*water.shape, 4), dtype=np.uint8)
        rgba[water] = [0, 105, 148, 180]

        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(rgba, interpolation='nearest')
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        plt.close()
        return img_str

    def _precipitationToImage(self, precipitation):
        """Convert precipitation array to base64 PNG, transparent where there is none"""
        normalized = precipitation / precipitation.max() if precipitation.max() > 0 else precipitation
        cmap = plt.cm.YlGnBu
        rgba = (cmap(normalized) * 255).astype(np.uint8)
        rgba[precipitation == 0, 3] = 0

        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(rgba, interpolation='nearest')
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        plt.close()
        return img_str

    def _humidityToImage(self, humidity):
        """Convert humidity array to base64 PNG"""
        humidity = np.array(humidity, dtype=float)
        normalized = (humidity - humidity.min()) / (humidity.max() - humidity.min())
        cmap = plt.cm.Blues
        rgba = (cmap(normalized) * 255).astype(np.uint8)

        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(rgba, interpolation='nearest')
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        plt.close()
        return img_str

    def _dataToImage(self, data, cmap='Blues'):
        """Convert a 2D data array to a base64 PNG using a colormap"""
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(data, cmap=cmap, interpolation='nearest')
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        plt.close()
        return img_str

    def _addDataLayer(self, m, data, cmap, label, show=False):
        """Add a static data layer to the map"""
        img_str = self._dataToImage(data, cmap=cmap)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{img_str}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.6,
            name=label,
            show=show
        ).add_to(m)

    def saveTimeline(self, filename='fire_simulation.html'):
        m = folium.Map(
            location=[(self.southLat + self.northLat) / 2, (self.westLon + self.eastLon) / 2],
            zoom_start=10
        )

        # Water layer - transparent non-water cells
        water_img = self._waterToImage(self.sim.grid.water)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{water_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.8,
            name='Water',
            show=False
        ).add_to(m)

        # Elevation layer
        self._addDataLayer(m, self.sim.grid.elevation, cmap='terrain', label='Elevation (m)')

        # Precipitation layer - transparent where no rain
        precip_img = self._precipitationToImage(self.sim.grid.precipitation)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{precip_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.8,
            name='Precipitation (mm)',
            show=False
        ).add_to(m)

        # Humidity layer
        humidity_img = self._humidityToImage(self.sim.grid.humidity)
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{humidity_img}",
            bounds=[[self.southLat, self.westLon], [self.northLat, self.eastLon]],
            opacity=0.6,
            name='Humidity (%)',
            show=False
        ).add_to(m)

        # Layer control for static layers
        folium.LayerControl(collapsed=False).add_to(m)

        # Generate images for fire simulation
        images = []
        for record in self.sim.history:
            images.append(self._stateToImage(record['state']))

        images_js = str([f"data:image/png;base64,{img}" for img in images])
        times_js = str([record['time'] for record in self.sim.history])
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
                    // Get map instance
                    for (var key in window) {{
                        try {{
                            if (window[key] && window[key]._leaflet_id !== undefined && window[key].addLayer) {{
                                map = window[key];
                                break;
                            }}
                        }} catch(e) {{}}
                    }}

                    // Pre-create all overlay layers at opacity 0 and add to map
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
                document.getElementById('timeLabel').innerText = times[step].toFixed(1);

                if (map && layers) {{
                    var img = new Image();
                    img.onload = function() {{
                        requestAnimationFrame(function() {{
                            layers[step].setOpacity(0.6);
                            if (currentLayer && currentLayer !== layers[step]) {{
                                currentLayer.setOpacity(0);
                            }}
                            currentLayer = layers[step];
                        }});
                    }};
                    img.src = images[step];
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
                        if (current >= totalSteps - 1) {{
                            current = 0;
                        }} else {{
                            current++;
                        }}
                        showStep(current);
                    }}, intervalMs);
                }}
            }});
        </script>
        """

        m.get_root().html.add_child(folium.Element(slider_html))
        m.save(filename)
        print(f"Saved to {filename}")