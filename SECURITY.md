# Security Policy

## Supported Versions

Security fixes are applied to the `main` branch. The project is a demo/educational
reference implementation; no backport releases are maintained.

## Reporting a Vulnerability

If you find a security issue, please report it privately by opening a
[security advisory](https://github.com/vishnuskandha/IoT-Pipeline-Leak-Detection/security/advisories)
or by emailing the maintainer. Do not open a public issue for vulnerabilities
that involve credentials, deployment secrets, or remote code execution.

Please include:

- A description of the issue and the affected components.
- Steps to reproduce (if applicable).
- The impact you observed.

We will acknowledge reports within 7 days and aim to release a fix on `main`
as soon as it is verified.

## Known Notes

- The Streamlit dashboard in `app.py` ships default demo credentials
  (`admin`/`admin123`, `operator`/`op123`, `viewer`/`view123`) so it can run
  out of the box. These are for local evaluation only. Before any production
  or internet-facing deployment, move authentication to environment variables
  or a secrets manager and change all passwords.
- The backend stores data in memory only (`HISTORY`) and exposes open CORS
  origins by default so local ESP32 boards can post readings. Restrict
  `ALLOWED_ORIGINS` and add authentication if the API is reachable beyond a
  trusted LAN.
- The backend is a simulator (`simulate_sensor_reading`) and rule-based leak
  scoring. It is not certified for safety-critical use.
