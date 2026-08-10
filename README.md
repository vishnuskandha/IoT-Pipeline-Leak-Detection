# IoT-Pipeline-Leak-Detection

[![CI](https://github.com/vishnuskandha/IoT-Pipeline-Leak-Detection/actions/workflows/ci.yml/badge.svg)](https://github.com/vishnuskandha/IoT-Pipeline-Leak-Detection/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Real-time leak detection for underground water pipelines. ESP32 Modbus RTU
slave nodes read flow, turbidity, and TDS sensors from the field, a master
ESP32 aggregates the readings over an RS485 bus and posts them to a FastAPI
backend, and a Streamlit dashboard renders live metrics, leak localization,
alert history, and rule-based predictive maintenance.

## Features

- Multi-node field architecture: 1 master + 3 slave nodes over Modbus RTU (RS485).
- Master ESP32 with on-site OLED status display (SSD1306).
- FastAPI ingestion API (`/api/sensor-data`) with CORS support for the dashboard.
- Streamlit dashboard with role-based login (Admin / Operator / Viewer).
- Live monitoring: pressure, flow, vibration, turbidity, TDS per sensor node.
- Leak localization: estimated leak node and distance from the pipeline start.
- Alert history: logs status changes with per-node filtering.
- Predictive maintenance (Level 1): explainable drift/volatility risk scoring
  with expected-issue-window heuristics and dominant-factor breakdown.
- Self-contained demo backend that simulates sensor readings with injected
  anomalies, so the full stack runs without hardware.
- `mock_esp32_post.ino` lets you simulate an ESP32 node from the Arduino IDE.

## Architecture

```
+-----------------------------------------------------------+
|                        Field Level                        |
|                                                           |
|   Slave Node 1  --\                                        |
|   Slave Node 2  --- Modbus RTU over RS485 bus -->  Master |
|   Slave Node 3  --/                          (ESP32)      |
|                                                           |
|   Each slave: flow sensor + turbidity + TDS               |
+-----------------------------------------------------------+
                       | HTTP POST (JSON) over WiFi
                       v
+-----------------------------------------------------------+
|   Backend (FastAPI, backend.py)                           |
|   - /api/health          health check                     |
|   - /api/sensor-data     ingest ESP32 readings            |
|   - /api/latest/{id}     latest reading per node          |
|   - /api/history/{id}    history buffer per node          |
|   - /api/predictive/{id} Level-1 risk scoring             |
+-----------------------------------------------------------+
                       | JSON over HTTP
                       v
+-----------------------------------------------------------+
|   Dashboard (Streamlit, app.py)                           |
|   - login / roles                                          |
|   - live metrics + trends                                  |
|   - leak localization                                      |
|   - alert history                                          |
|   - predictive maintenance tab                             |
+-----------------------------------------------------------+
```

## Quickstart

Prerequisites: Python 3.9+.

### Backend and dashboard

```bash
git clone https://github.com/vishnuskandha/IoT-Pipeline-Leak-Detection.git
cd IoT-Pipeline-Leak-Detection

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn backend:app --host 0.0.0.0 --port 8000
```

Start the dashboard in a second terminal:

```bash
streamlit run app.py
```

Open http://localhost:8501 and sign in with one of the demo accounts:
`admin`/`admin123`, `operator`/`op123`, or `viewer`/`view123`.

The dashboard defaults to `http://127.0.0.1:8000`. To point it elsewhere,
set the `BACKEND_URL` environment variable or add it under Streamlit secrets
(`.streamlit/secrets.toml`).

### Flash the ESP32 firmware

Install the Arduino libraries `ModbusMaster`, `ModbusRTU`, `Adafruit SSD1306`,
`Adafruit GFX`, `HTTPClient`, and `WiFi` from the Library Manager.

1. Open `esp32_master.ino`. Set your WiFi `ssid`/`password` and set
   `serverUrl` to your PC's IP (e.g. `http://192.168.0.3:8000/api/sensor-data`).
   Flash to the master board.
2. Open `esp32_slave.ino`. Set `#define SLAVE_ID` to `1`, `2`, or `3` for each
   board. Flash to three slave boards.
3. `esp32_slave_serial.ino` is a debug variant that also prints readings over
   the serial monitor.

See [ESP32_Modbus_Walkthrough.md](ESP32_Modbus_Walkthrough.md) for the full
hardware wiring (RS485 daisy chain, MAX485 pin mapping, sensor wiring, and
OLED hookup) and verification steps.

### Simulate a node without hardware

Flash `mock_esp32_post.ino` (after setting your WiFi and backend URL) to any
ESP32, or simply exercise the API:

```bash
curl -X POST http://127.0.0.1:8000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d "{\"node_id\":1,\"tds\":320,\"turbidity\":2.1,\"flow\":17.5,\"is_leak\":false}"
```

## Repository layout

```
app.py                   Streamlit dashboard (login, live metrics, predictive tab)
backend.py               FastAPI backend (ingestion, history, risk scoring)
esp32_master.ino         ESP32 master: polls slaves over RS485, posts to backend
esp32_slave.ino          ESP32 slave: reads sensors, serves Modbus registers
esp32_slave_serial.ino   Debug slave variant with serial prints
mock_esp32_post.ino      ESP32 sketch that posts simulated readings
ESP32_Modbus_Walkthrough.md  Hardware wiring and flashing guide
requirements.txt         Python dependencies
```

## Configuration

| Setting | Where | Notes |
| --- | --- | --- |
| `BACKEND_URL` | `app.py` / env / Streamlit secrets | Dashboard-to-backend URL |
| `ALLOWED_ORIGINS` | `backend.py` / env | Comma-separated CORS origins |
| `NODE_COUNT`, `NODE_SPACING_M` | `backend.py` | Pipeline geometry |
| Sensor thresholds | `esp32_master.ino` | Leak detection thresholds |
| `SLAVE_ID` | `esp32_slave.ino` | Unique per board (1, 2, 3) |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
development setup, code style, and validation steps.

## Security

See [SECURITY.md](SECURITY.md) for the supported-versions policy and notes on
the default demo credentials and memory-only storage.

## License

MIT License. See [LICENSE](LICENSE).
