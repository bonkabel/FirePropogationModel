# Fire Propagation Simulation

A grid-based wildfire spread simulator using the Canadian Fire Weather Index (FWI) and Fire Behaviour Prediction (FBP) systems, with a Minimum Travel Time (MTT) propagation model. Enter any geographic location and watch fire spread across real-world terrain and weather data.

Built with Python, Streamlit, and Folium.

https://firepropagationmodel.streamlit.app/

## Features

- Real-world weather data via [Open-Meteo API](https://open-meteo.com/)
- Elevation and land cover from Copernicus GLO-30 DEM and ESA WorldCover 2021
- Fire spread modelled as an ellipse using FWI (FFMC, ISI) and FBP (ROS, WSV, RAZ)
- Minimum Travel Time solver via Dijkstra's algorithm for accurate anisotropic spread
- Burnout modelling: extinguished cells cannot ignite neighbours
- Two fuel types: C-2 Boreal Spruce (forested) and O-1 Grass (open)
- Interactive Folium map with toggleable overlays: wind, elevation, humidity, precipitation, fire affinity (ISI), and water
- Time-stepped animation with a slider to go through fire progression

## Installation

### Prerequisites

- Python 3.9 or later
- pip
- An active internet connection (for weather, terrain, and geocoding data)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/fire-propagation-simulation.git
cd fire-propagation-simulation
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up API keys

This project uses the [OpenCage Geocoding API](https://opencagedata.com/) to convert location strings to coordinates.

Create a `.streamlit/secrets.toml` file in the project root:

```toml
[opencage]
api_key = "your_opencage_api_key_here"
```

> **Note:** Never commit this file to version control. It is listed in `.gitignore` by default.

## Running Locally

```bash
streamlit run main.py
```

Then open `http://localhost:8501` in your browser.

## Usage

1. Enter a location (e.g. `"Yao, Chad, Africa"` or decimal coordinates).
2. Select grid size and weather mode (current forecast or 6-day historical average).
3. Click Run Simulation.
4. Explore the interactive map, toggle overlays and go through the fire timeline.

## Data Sources

| Data | Source |
|------|--------|
| Weather | [Open-Meteo](https://open-meteo.com/) |
| Elevation | [Copernicus GLO-30 DEM](https://spacedata.copernicus.eu/) |
| Land Cover | [ESA WorldCover 2021](https://esa-worldcover.org/) |
| Geocoding | [OpenCage](https://opencagedata.com/) |

## Background

- **FWI System**: Van Wagner, C.E. (1987). *Development and structure of the Canadian Forest Fire Weather Index System.* Forestry Technical Report 35.
- **FBP System**: Forestry Canada (1992). *Development and structure of the Canadian Forest Fire Behavior Prediction System.* ST-X-3.
- **Fire Ellipse Model**: Alexander, M.E. (1985); Richards, G.D. (1995).
- **MTT Method**: Finney, M.A. (2002). *Fire growth using minimum travel time methods.* Canadian Journal of Forest Research, 32(8).

## Limitations

- Weather is fixed at simulation start
- Two fuel types only (C-2 and O-1); no full FBP fuel mapping
- No spotting (ember transport) modelled
- BUI/BE drought adjustment not yet implemented
- Burnout duration uses a heuristic model, not FBP-derived
