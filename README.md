# Adaptive EV Charging Ecosystem — Flask prototype

A runnable academic prototype that demonstrates the main algorithmic components in the project abstract:

1. Dynamic multi-weight road/network graph and weighted Dijkstra route selection.
2. Multi-criteria charging-station ranking using price, wait, renewable share, grid load, carbon and battery-impact indicators.
3. Bipartite maximum matching between EV connector requirements and available charging ports.
4. Greedy graph coloring for a sample conflict-free charging schedule.
5. Minimum-cost energy flow with residual reverse edges and Bellman–Ford shortest augmenting paths.
6. Greedy dominating-set approximation for charging-station/service-zone coverage.
7. Adaptive priority ordering based on emergency flag, state of charge and deadline.
8. Interactive Leaflet map using OpenStreetMap tiles.

## Windows / VS Code setup

1. Install Python 3.10+ and VS Code.
2. Extract this ZIP to a folder such as `C:\Users\YourName\adaptive_ev_complete`.
3. In VS Code, choose **File → Open Folder** and select `adaptive_ev_complete`.
4. Open **Terminal → New Terminal**. Confirm you are in the folder containing `app.py` and `requirements.txt` by running `dir`.
5. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`, or run `py -m pip install -r requirements.txt` without activating.

6. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

7. Start the site:

   ```powershell
   py app.py
   ```

8. Open `http://127.0.0.1:5000` in your browser. Keep the terminal running while using the site.

## Important research limitations

- Coordinates and all EV/station/energy-network values are synthetic demonstration values, not a live Vellore charger feed.
- The map needs an internet connection to load OpenStreetMap tiles.
- Road edges are illustrative straight-line map connections; route metrics are modeled, not actual navigation directions or traffic ETAs.
- The route solver uses a weighted sum and returns one route; it does not compute the complete Pareto-optimal set.
- Station ranking is a transparent prototype score. Calibrate units, normalization and weights before evaluating it scientifically.
- Matching, graph coloring and minimum-cost flow operate on the small sample dataset. The flow “units” and “cost index” are not measured kWh, rupees or grid dispatch values.
- The dominating-set result is greedy and approximate, not guaranteed globally minimal.
- No live IoT, charger operator, vehicle telemetry, weather, tariff, traffic or grid API is integrated. Do not claim real-world performance gains without experiments and evidence.

## Project structure

```text
adaptive_ev_complete/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── style.css
```
