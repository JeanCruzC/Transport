# Gestión de Rutas de Transporte

This repository contains a Streamlit application that simulates a transportation route management system. The app lets you view drivers, schedule routes and visualize them on an interactive map. It also provides basic analytics for distance and cargo transported.

## Installation

1. Make sure you have **Python 3.8+** installed.
2. (Optional) Create and activate a virtual environment.
3. Install the required packages:

```bash
pip install streamlit pandas folium streamlit-folium plotly
```

## Running the app

Execute the following command from the project folder:

```bash
streamlit run Transporte.py
```

Your default browser will open with the application.

## Usage

The sidebar contains a menu to access different pages:

- **Dashboard** – overall metrics and charts summarizing drivers and routes.
- **Conductores** – table of drivers with filtering and a form to add new ones.
- **Rutas** – list of routes with filters and a planner form.
- **Mapa de Rutas** – Folium map showing the origin and destination of each route.
- **Análisis** – charts for distance, cargo and a summary table by driver.

Feel free to modify the sample data or extend the features as needed.
