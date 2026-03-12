# CLAUDE.md — AI Assistant Guide for Ragnar

## Project Overview

**Ragnar** is a Python-based network reconnaissance, vulnerability assessment, and offensive security tool. It is an enhanced fork of the Bjorn project designed for IoT/network penetration testing. The tool runs on three platform targets:

1. **Raspberry Pi + e-Paper HAT** — Autonomous scanning with status displayed on a Waveshare 2.13" e-Paper display
2. **Headless Server** — Full-featured mode for Debian/Ubuntu servers (recommended: 8GB+ RAM)
3. **WiFi Pineapple Pager** — Embedded payload running on MIPS hardware with an LCD display

**License:** MIT
**Language:** Python 3
**Primary Framework:** Flask + Flask-SocketIO

---

## Repository Layout

```
Ragnar/
├── Ragnar.py                   # Entry point: display mode (Raspberry Pi + e-Paper)
├── headlessRagnar.py           # Entry point: headless server mode
├── PagerRagnar.py              # Entry point: WiFi Pineapple Pager mode
│
├── orchestrator.py             # Core attack orchestration & scheduling
├── webapp_modern.py            # Flask web server + all API endpoints + WebSocket (~15k lines)
├── db_manager.py               # SQLite database management (~2.7k lines)
├── shared.py                   # Shared in-memory data structures
├── init_shared.py              # Initializes shared_data at startup
│
├── ai_service.py               # OpenAI GPT-5 Nano integration (optional)
├── auth_manager.py             # Authentication, password hashing, DB encryption
├── attack_logger.py            # Attack execution logging
├── logger.py                   # Custom Rich-based console logger
├── threat_intelligence.py      # CISA KEV, NVD CVE, AlienVault OTX, MITRE ATT&CK
├── network_intelligence.py     # Network data analysis and summarization
├── device_classifier.py        # Device type classification (MAC OUI + heuristics)
├── advanced_vuln_scanner.py    # Nuclei, Nikto, SQLMap, ZAP integration
├── traffic_analyzer.py         # Real-time traffic analysis (tcpdump, tshark)
├── wifi_manager.py             # WiFi connections, AP mode, captive portal
├── wifi_interfaces.py          # Network interface enumeration
├── multi_interface.py          # Multi-interface support
├── comment.py                  # AI commentary generation
├── utils.py                    # General utility functions
├── env_manager.py              # .env / environment variable management
│
├── display.py                  # Waveshare e-Paper HAT driver integration
├── pager_display.py            # WiFi Pineapple Pager LCD display
├── pager_menu.py               # Pager menu system
├── pagerctl.py                 # Pager control interface
├── epd_helper.py               # e-Paper display helpers
├── epd_button.py               # e-Paper button interface
├── pisugar_button.py           # PiSugar 3 UPS integration
│
├── actions/                    # Plugin-based attack/scan modules
│   ├── IDLE.py                 # Idle state
│   ├── Scanner.py              # Discovery scanner
│   ├── scanning.py             # Full nmap-based network scan (~105k lines)
│   ├── nmap_vuln_scanner.py    # NSE-based vulnerability scanning (~46k lines)
│   ├── ble.py                  # BLE scanning
│   ├── ble_pentest.py          # BLE penetration testing
│   ├── ftp_connector.py        # FTP brute-force / file theft
│   ├── ssh_connector.py        # SSH brute-force / file theft
│   ├── smb_connector.py        # SMB exploitation
│   ├── rdp_connector.py        # RDP brute-force
│   ├── telnet_connector.py     # Telnet attacks
│   ├── sql_connector.py        # SQL database attacks
│   ├── steal_files_*.py        # File exfiltration modules (6 variants)
│   ├── steal_data_sql.py       # SQL data exfiltration
│   └── lynis_pentest_ssh.py    # SSH-based Lynis security auditing
│
├── config/
│   ├── actions.json            # Attack plugin registry (name, module, enabled flag)
│   └── routes.json             # Web API endpoint definitions
│
├── web/
│   ├── index_modern.html       # Main dashboard SPA (~313k bytes)
│   ├── login.html              # Auth page
│   ├── wifi_config.html        # WiFi config portal
│   ├── captive_portal.html     # Fallback captive portal
│   ├── css/                    # Stylesheets
│   ├── scripts/                # Frontend JavaScript
│   └── images/                 # UI assets
│
├── tests/
│   ├── conftest.py             # Adds project root to sys.path
│   ├── test_env_manager.py
│   ├── test_orchestrator_semaphore.py
│   └── test_pager_code.py
│
├── data/                       # Runtime data (created at first run)
│   ├── ragnar.db               # Main SQLite database
│   ├── ragnar.db.enc           # Encrypted DB backup (when auth enabled)
│   ├── input/                  # Wordlists and attack inputs
│   ├── networks/               # Per-network results
│   └── logs/                   # Application logs
│
├── resources/
│   ├── comments/               # AI comment text bank
│   ├── fonts/                  # Display fonts
│   ├── images/                 # Display images
│   └── waveshare_epd/          # e-Paper display drivers
│
├── pager_lib/                  # Pre-compiled MIPS libraries for Pager deployment
├── scripts/                    # Maintenance shell scripts
├── docs/                       # Documentation mirror
│
├── requirements.txt            # Python dependencies
├── .pylintrc                   # Pylint configuration (fail-under=8)
├── .gitignore
└── install_ragnar.sh           # Main installer (multi-distro)
```

---

## Running the Application

```bash
# Headless mode (development / server)
python3 headlessRagnar.py

# Display mode (Raspberry Pi with e-Paper HAT)
python3 Ragnar.py

# WiFi Pineapple Pager mode
python3 PagerRagnar.py

# Via systemd service (production)
sudo systemctl start ragnar
sudo systemctl status ragnar
sudo journalctl -u ragnar -f     # Follow logs
```

The web dashboard is served at `http://<host>:8000` by default.

---

## Running Tests

```bash
# Run all tests from project root
pytest tests/

# Run a specific test file
pytest tests/test_env_manager.py
pytest tests/test_pager_code.py
pytest tests/test_orchestrator_semaphore.py

# Verbose output
pytest tests/ -v
```

`tests/conftest.py` automatically adds the project root to `sys.path` so root-level modules can be imported without installing the package.

---

## Linting

```bash
# Run pylint on a module
pylint webapp_modern.py

# Run pylint on entire project (ignores venv, node_modules, scripts)
pylint *.py actions/*.py

# Minimum passing score: 8.0/10 (configured in .pylintrc)
```

The `.pylintrc` at the project root configures pylint with:
- `fail-under=8` — PRs should not drop score below 8.0
- `ignore=venv,node_modules,scripts` — these directories are excluded

---

## Architecture & Key Patterns

### Entry Points
Each platform variant (`Ragnar.py`, `headlessRagnar.py`, `PagerRagnar.py`) initializes `shared_data` via `init_shared.py`, starts the orchestrator, and launches the Flask web server.

### Plugin-Based Action System
Attack/scan modules live in `actions/` and are registered in `config/actions.json`. The orchestrator (`orchestrator.py`) loads, schedules, and executes these plugins dynamically. Each action module exposes a standard interface consumed by the orchestrator.

### Shared State
`shared.py` defines the central `shared_data` dict that holds in-memory state: discovered hosts, attack results, scan progress, config. Access is guarded by `threading.RLock`. This object is passed through the app rather than using global variables.

### Database
`db_manager.py` manages a single SQLite database at `data/ragnar.db` with tables for hosts, open ports, credentials, vulnerabilities, and attack status per host. When authentication is enabled, `auth_manager.py` can transparently encrypt the database file to `data/ragnar.db.enc` using AES-128 (Fernet) with PBKDF2-derived keys (200k iterations).

### Web Server
`webapp_modern.py` is the monolithic Flask application. It handles:
- REST API endpoints defined in `config/routes.json`
- WebSocket events via `flask-socketio` for real-time dashboard updates
- Serving `web/` static assets

### Real-Time Communication
The frontend dashboard (`web/index_modern.html`) is a single-page application that connects via WebSocket (Socket.IO) for live updates: scan progress, attack events, new findings.

### Authentication
`auth_manager.py` implements:
- Hardware fingerprint-bound authentication (Raspberry Pi serial / network MAC)
- PBKDF2-SHA256 password hashing (200,000 iterations)
- 24-hour session expiration
- Kill switch endpoint for full database wipe (`KILL_SWITCH.md`)

### AI Integration (Optional)
`ai_service.py` wraps the OpenAI API (GPT-5 Nano) for:
- Network scan summaries
- Vulnerability analysis commentary
Requires `OPENAI_API_KEY` in the environment. Feature degrades gracefully when key is absent.

### Threading Model
- Each attack module typically runs in its own `threading.Thread`
- The orchestrator uses semaphores to limit concurrent attacks
- `wifi_manager.py` runs background threads for connection monitoring
- Tests for thread safety are in `tests/test_orchestrator_semaphore.py`

---

## Configuration Files

| File | Purpose |
|------|---------|
| `config/actions.json` | Lists all attack plugins: name, Python module path, enabled flag, display order |
| `config/routes.json` | Maps web API routes to handler functions in `webapp_modern.py` |
| `.env` (not committed) | Secrets: `OPENAI_API_KEY`, `PUSHOVER_TOKEN`, etc. |
| `.pylintrc` | Pylint rules, fail threshold, ignored paths |

### Environment Variables (via `.env` or shell)

| Variable | Purpose | Required |
|----------|---------|---------|
| `OPENAI_API_KEY` | GPT-5 Nano AI features | No |
| `PUSHOVER_TOKEN` | Push notification service | No |
| `PUSHOVER_USER` | Pushover user key | No |
| `RAGNAR_PORT` | Web server port (default: 8000) | No |

---

## Python Dependencies

Key packages from `requirements.txt`:

| Package | Use |
|---------|-----|
| `Flask>=3.0.0` | Web server |
| `flask-socketio>=5.3.0` | WebSocket real-time updates |
| `flask-cors>=4.0.0` | CORS headers |
| `python-nmap>=0.7.0` | Nmap Python wrapper |
| `paramiko>=3.0.0` | SSH client (brute-force, file ops) |
| `smbprotocol>=1.10.0` | SMB/CIFS protocol |
| `pysmb>=1.2.0` | SMB client |
| `pymysql>=1.0.0` | MySQL client |
| `sqlalchemy>=1.4.0` | ORM |
| `cryptography>=41.0.0` | AES encryption, key derivation |
| `openai>=2.0.0` | GPT API client |
| `rich>=13.0.0` | Colorized console output |
| `Pillow>=10.0.0` | Image processing (display) |
| `numpy>=1.24.0` | Numerical ops |
| `pandas>=2.0.0` | Data analysis |
| `netifaces==0.11.0` | Network interfaces |
| `psutil>=5.9.0` | System resource monitoring |
| `RPi.GPIO==0.7.1` | Raspberry Pi GPIO (Pi only) |
| `pisugar>=1.0.0` | PiSugar UPS (Pi only) |

Install all dependencies:
```bash
pip3 install -r requirements.txt
```

---

## External Tool Dependencies

These system tools are installed by `install_advanced_tools.sh` and used at runtime:

| Tool | Purpose |
|------|---------|
| `nmap` | Core network scanning |
| `nuclei` | Template-based vulnerability scanning |
| `nikto` | Web server security scanning |
| `sqlmap` | SQL injection testing |
| `zaproxy` | OWASP ZAP web app scanning |
| `tshark` / `tcpdump` | Traffic capture and analysis |
| `whatweb` | Web application fingerprinting |

---

## Database Schema

**`data/ragnar.db`** (SQLite) core tables:

- **`hosts`** — Discovered network hosts: `ip`, `mac`, `hostname`, `os`, `vendor`, `status`, `last_seen`, `failed_ping_count`, per-action status columns
- Per-host attack status columns follow the pattern `<action_name>_status` (e.g., `ssh_connector_status`, `smb_connector_status`)
- **`ports`** — Open ports per host: `host_id`, `port`, `protocol`, `service`, `version`
- **`vulnerabilities`** — CVEs and findings: `host_id`, `cve_id`, `severity`, `description`, `source`
- **`credentials`** — Captured credentials: `host_id`, `service`, `username`, `password`

**`data/ragnar_auth.db`** (SQLite) — Authentication data (separate from main DB):
- User accounts with PBKDF2 hashed passwords
- Hardware fingerprint binding
- Wrapped encryption keys
- Recovery codes

---

## Code Conventions

### Logging
Use the custom `Logger` class from `logger.py` (wraps Python `logging` + `Rich`):
```python
from logger import Logger
logger = Logger(name="my_module")
logger.info("Message")
logger.warning("Warning")
logger.error("Error")
```
Do not use `print()` for application output.

### Error Handling
- Use broad `try/except` blocks around hardware-dependent code (GPIO, SPI, e-Paper) since these will fail on non-Pi systems
- Attack modules should catch and log exceptions without crashing the orchestrator
- Use `logger.error(str(e))` with descriptive context strings

### Threading
- Access `shared_data` through `shared_data['lock']` (RLock) when reading/writing mutable state
- Attack plugins should check a stop flag periodically to support graceful shutdown
- Avoid `time.sleep()` in tight loops; use threading events instead

### Adding a New Attack Module
1. Create `actions/my_attack.py` implementing the standard action interface
2. Add an entry to `config/actions.json`:
   ```json
   {
     "name": "my_attack",
     "module": "actions.my_attack",
     "enabled": true,
     "display_name": "My Attack",
     "priority": 50
   }
   ```
3. The orchestrator will automatically discover and schedule it

### Frontend (JavaScript)
- The dashboard is a vanilla JS SPA in `web/index_modern.html`
- Uses Socket.IO client for real-time events
- D3.js for network topology visualization
- No build step — changes to HTML/CSS/JS are immediately reflected

---

## Platform-Specific Notes

### Raspberry Pi
- GPIO and SPI libraries (`RPi.GPIO`, `spidev`) are only available on Pi hardware
- Import failures for these are caught and handled gracefully in `display.py`
- The installer creates `/etc/systemd/system/ragnar.service`

### Headless / Server Mode
- No display hardware required
- `advanced_vuln_scanner.py` features (Nuclei, Nikto, ZAP) require 8GB+ RAM
- Run `install_advanced_tools.sh` separately for optional tools

### WiFi Pineapple Pager
- Targets MIPS architecture; pre-compiled libraries are in `pager_lib/`
- Deployed via `install_pineapple_pager.sh` over SSH
- Uses `libpagerctl.so` (binary) for LCD and button control via `pagerctl.py`

---

## Security Considerations

This tool is designed for **authorized penetration testing only**.

- Never run against networks without explicit written authorization
- The kill switch endpoint (`/api/kill`) wipes all collected data — document before use
- Credentials captured during testing are stored in plaintext in `data/ragnar.db` — encrypt using the auth system in production
- The `.env` file (API keys, secrets) must never be committed to version control

---

## Development Workflow

```bash
# 1. Clone and set up
git clone https://github.com/PierreGode/Ragnar.git
cd Ragnar
pip3 install -r requirements.txt

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Run tests before and after changes
pytest tests/ -v

# 4. Lint your code
pylint your_module.py   # Score must be >= 8.0

# 5. Commit with descriptive messages
git commit -m "feat: Add feature description"

# 6. Push and open a PR against master
git push origin feature/your-feature-name
```

### Commit Message Convention
```
feat: Add new capability
fix: Correct bug in module
refactor: Simplify orchestrator scheduling
test: Add coverage for wifi_manager
docs: Update CLAUDE.md
```

---

## Files to Avoid Modifying Without Understanding

| File | Reason |
|------|--------|
| `webapp_modern.py` | Monolithic 15k-line Flask app; changes can break API or WebSocket contracts |
| `db_manager.py` | Schema changes require migration; broken DB breaks the entire app |
| `auth_manager.py` | Encryption/auth logic — bugs can lock out users or expose data |
| `actions/scanning.py` | 105k-line nmap integration; highly stateful |
| `shared.py` | Central data structure; interface changes cascade everywhere |
| `pager_lib/` | Pre-compiled MIPS binaries — do not modify or rebuild without a MIPS toolchain |

---

## Key Files Quick Reference

| Task | File |
|------|------|
| Start the app | `headlessRagnar.py`, `Ragnar.py`, `PagerRagnar.py` |
| Add an API endpoint | `webapp_modern.py` + `config/routes.json` |
| Add an attack module | `actions/<module>.py` + `config/actions.json` |
| Modify DB schema | `db_manager.py` |
| Change scan behavior | `actions/scanning.py`, `orchestrator.py` |
| Modify web dashboard | `web/index_modern.html`, `web/scripts/`, `web/css/` |
| Adjust auth logic | `auth_manager.py` |
| Modify AI responses | `ai_service.py`, `comment.py` |
| Modify display output | `display.py` (Pi), `pager_display.py` (Pager) |
| Add environment config | `env_manager.py`, `.env` |
