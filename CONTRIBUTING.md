# Contributing to IoT-Pipeline-Leak-Detection

Thanks for your interest in contributing. This project is a reference
implementation of a water pipeline leak detection system using ESP32 Modbus
RTU slaves, a FastAPI backend, and a Streamlit dashboard.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Make your changes, following the guidelines below.
4. Run the checks described under "Validation".
5. Open a pull request against `main` and describe what you changed and why.

## Development Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn backend:app --reload --host 0.0.0.0 --port 8000
```

Run the dashboard in a second terminal:

```bash
streamlit run app.py
```

## Code Style

- Follow PEP 8 for Python.
- Keep functions small and focused.
- Add docstrings to new functions that explain non-obvious logic.
- Do not hardcode credentials. Use `os.getenv(...)` and configuration
  files that are gitignored (`.env`, `.streamlit/secrets.toml`).

## Validation

Before submitting a pull request:

1. Make sure the code compiles:
   ```bash
   python -m py_compile app.py backend.py
   ```
2. Start the backend and confirm `/api/health` returns `{"status":"ok"}`.
3. Load the dashboard and confirm metrics render and alert history logs
   status changes.
4. If you touched firmware (`.ino`) files, verify the Arduino sketch
   compiles in Arduino IDE with the libraries listed in
   `ESP32_Modbus_Walkthrough.md`.

## Commit Guidelines

- Use clear, descriptive commit messages (`git commit -m "Add X to Y"`).
- Keep commits focused on one logical change.
- Do not commit secrets, `.env` files, or local configuration.

## License

By contributing you agree that your contributions are licensed under the
MIT License. See `LICENSE`.
