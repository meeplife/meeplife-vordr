## <img width="70" height="150" alt="image" src="https://github.com/user-attachments/assets/463d32c7-f6ca-447c-b62b-f18f2429b2b2" /> Ragnar

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/J3J2EARPK)
![GitHub stars](https://img.shields.io/github/stars/PierreGode/Ragnar)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)
![Status](https://img.shields.io/badge/Status-Development-blue.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/3bed08a1-b6cf-4014-9661-85350dc5becc" width="200"/></td>
    <td><img src="https://github.com/user-attachments/assets/88345794-edfc-49e8-90ab-48d72b909e86" width="800"/></td>
  </tr>
</table>
</p>

Ragnar is a « Tamagotchi like » sophisticated, autonomous network scanning, vulnerability assessment, and offensive security tool designed to run on a Raspberry Pi equipped with a 2.13-inch e-Paper HAT, a headless/server install on Debian-based systems (AMD64/ARM/ARM64) with Ethernet-first connectivity, or on the **WiFi Pineapple Pager** with full-color LCD display.

-
On servers with 8GB+ RAM, Ragnar unlocks advanced capabilities including real-time traffic analysis and enhanced vulnerability assessment. This document provides a detailed explanation of the project.

The fastest way to install Ragnar is using the automatic installation script :

```bash
# Download and run the installer
wget https://raw.githubusercontent.com/PierreGode/Ragnar/main/install_ragnar.sh
sudo chmod +x install_ragnar.sh && sudo ./install_ragnar.sh
# On Raspberry Pi you'll be asked if an e-Paper HAT is attached; on other hardware it auto-selects server (headless) mode with LAN-first networking.
# Option 3 deploys to a WiFi Pineapple Pager via SSH.
# It may take a while as many packages and modules will be installed. Reboot when it finishes.
```


### 🔨 Installation



### 🌐 Web Interface & WiFi Management

**Modern Dashboard** - Access Ragnar's sleek web interface at `http://<ragnar-ip>:8000`:
[Images](WEB.md)
- Real-time network discovery and vulnerability scanning
- Multi-source threat intelligence dashboard
- File management with image gallery
- System monitoring and configuration
- Hardware profile auto-detection (Pi Zero 2W, Pi 4, Pi 5)

**WiFi Configuration Portal** - When Ragnar can't connect to a known network, it automatically creates a WiFi hotspot:
1. **Connect** to WiFi network: `Ragnar` (password ragnarconnect)
2. **Navigate** to: `http://192.168.4.1:8000`
3. **Configure** your home WiFi credentials via the mobile-friendly interface
4. **Monitor** the countdown timer - Ragnar will automatically try to reconnect to kn wifi after som time if AP is unused.
5. **Done** - Ragnar exits AP mode and connects to your network

The AP portal features:
- Network scanning with signal strength indicators
- Manual network entry for hidden SSIDs
- Countdown timer showing when Ragnar will retry WiFi
- Known networks management
- One-tap connection to saved networks

## 📄 Introduction

Ragnar is a fork from the awesome project [Bjorn](https://github.com/infinition/Bjorn)  and is rebuilt powerful tool designed to perform comprehensive network scanning, vulnerability assessment, and data ex-filtration. Its modular design and extensive configuration options allow for flexible and targeted operations. By combining different actions and orchestrating them intelligently, Ragnar can provide valuable insights into network security and help identify and mitigate potential risks.

Ragnar is built for 64-bit Raspberry Pi OS (Debian Trixie). 

The e-Paper HAT display and web interface make it easy to monitor and interact with Ragnar, providing real-time updates and status information. With its extensible architecture and customizable actions, Ragnar can be adapted to suit a wide range of security testing and monitoring needs.

## 🌟 Features

- **Network Scanning**: Identifies live hosts and open ports on the network.
- **Vulnerability Assessment**: Performs vulnerability scans using Nmap and other tools.
- **Multi-Source Threat Intelligence**: Real-time threat intelligence fusion from CISA KEV, NVD CVE, AlienVault OTX, and MITRE ATT&CK.
- **AI-Powered Analysis**: 🆕 GPT-5 Nano integration provides intelligent analysis:
  - Network security summaries
  - Vulnerability prioritization and remediation advice
  - Network weakness identification and attack vector analysis
  - See [AI Integration Guide](AI_INTEGRATION.md) for setup
- **System Attacks**: Conducts brute-force attacks on various services (FTP, SSH, SMB, RDP, Telnet, SQL).
- **File Stealing**: Extracts data from vulnerable services.
- **Advanced Server Features (8GB+ RAM)**: 🆕
  - **Real-Time Traffic Analysis**: Live packet capture, connection tracking, protocol analysis, bandwidth monitoring, and C2 beacon detection using tcpdump, tshark, and custom analyzers
  - **Advanced Vulnerability Scanning**: Enhanced assessment with Nuclei templates, Nikto web server scanning, SQLMap injection testing, parallel scanning, CVE correlation, and exploit suggestion engine
- **LAN-First Connectivity**: Prefers Ethernet when present, exposes a LAN status card in the modern dashboard, and still manages WiFi as needed.
- **Smart WiFi Management**: 
  - Auto-connects to known networks on boot
  - Falls back to AP mode when no WiFi available
  - Captive portal at `http://192.168.4.1/portal` for easy mobile configuration
  - Automatic network reconnection with validation
- **Modern Web Interface**: 
  - Beautiful Tailwind CSS-based dashboard
  - Real-time updates via WebSocket
  - Comprehensive network visualization
  - AI-powered insights on dashboard
  - Threat intelligence dashboard
  - File management and image gallery
  - System monitoring and configuration
  - Hardware profile auto-detection for optimal performance
- **E-Paper Display**: Real-time status display showing targets, vulnerabilities, credentials, and network info including IP address.
- **WiFi Pineapple Pager Support**: Full-color LCD display with button controls, LED status indicators, graphical menus, and auto-dim for battery saving. Runs as a native Pager payload.
- **Hardware-Bound Authentication**: Optional login system that encrypts the database at rest and binds access to the device hardware. Recovery codes provided for password reset. See [Security & Authentication](SECURITY.md) for details.
- **PiSugar 3 Button Support**: Physical button swap between Ragnar and Pwnagotchi modes. Double tap or long press to switch. Single tap toggles manual mode. Works in both directions — no SSH or web UI needed.
- **Comprehensive Logging**: All nmap commands and their results are automatically logged to `data/logs/nmap.log` for audit trails and troubleshooting.

<p align="center">
  <img width="150" height="300" alt="image" src="https://github.com/user-attachments/assets/463d32c7-f6ca-447c-b62b-f18f2429b2b2" />
</p>

<img width="1092" height="902" alt="image" src="https://github.com/user-attachments/assets/cafed68d-de62-4041-aa36-c1fcccacc9ea" />



## 🚀 Getting Started

## 📌 Prerequisites

### 📋 Prerequisites for RPI zero W + W2 (64bits)

- Raspberry Pi OS installed. 
    - Stable:
      - System: 64-bit
      - Kernel version: 6.12
      - Debian version: Debian GNU/Linux 13 (trixie)'
- Username and hostname set to `ragnar`.
- 2.13-inch e-Paper HAT connected to GPIO pins.

### 📋 Prerequisites for Debian-based Server/Headless Installation

- **Operating System**: Debian 11+ or Ubuntu 20.04+ (AMD64, ARM64, or ARMv7)
- **Architecture Support**: AMD64 (x86_64), ARM64 (aarch64), ARMv7l, ARMv8l
- **Minimum Resources**: 2GB RAM, 2 CPU cores, 10GB free disk space
- **Recommended for Advanced Features**: 8GB+ RAM to unlock:
  - Real-time traffic analysis with packet capture
  - Advanced vulnerability scanning (Nuclei, Nikto, SQLMap)
  - Parallel scanning capabilities
  - Enhanced threat detection

Ragnar is built for 64 bit trixie and
Waveshare 2.13inch E-Paper Display HAT V4 for 32 bit system i recommend using Ragnars son [Bjorn](https://github.com/infinition/Bjorn)

### 📋 Prerequisites for WiFi Pineapple Pager

- WiFi Pineapple Pager (firmware 1.0.7+)
- PAGERCTL payload installed on the Pager
- Network connection for first-run dependency installation (Python3, nmap)
- SSH access to the Pager from your workstation
- [pineapple_pager_bjorn](https://github.com/brAinphreAk/pineapple_pager_bjorn) cloned alongside Ragnar (provides MIPS-compiled Python libraries)


#### Reccomendation
- In nano, edit ~/.config/labwc/autostart and comment out the line
#/usr/bin/lwrespawn /usr/bin/wf-panel-pi &
(This disables the unneeded desktop panel that consumes resources.)
- Ot sudo pkill wf-panel-pi to kill itt temporary 

### 🔨 Installation

The fastest way to install Ragnar is using the automatic installation script :

```bash
# Download and run the installer
wget https://raw.githubusercontent.com/PierreGode/Ragnar/main/install_ragnar.sh
sudo chmod +x install_ragnar.sh && sudo ./install_ragnar.sh
# On Raspberry Pi: choose between e-Paper HAT, server/headless, or Pineapple Pager deployment.
# On other hardware: choose between server install or Pineapple Pager deployment.
# It may take a while as many packages and modules will be installed. Reboot when it finishes.
```

**Installer intelligence:**
- Auto-detects distro/package manager (apt, dnf, pacman, zypper) and CPU arch to install the right package names.
- **Debian System Support**: Full compatibility with Debian-based distributions on ARM, ARM64, and AMD64 architectures.
- Profiles: **Pi + e-Paper** (display enabled), **Server/Headless** (no display, modern web UI only), or **WiFi Pineapple Pager** (full-color LCD). Non-Pi hardware defaults to Server/Headless.
- **Automatic Advanced Tools**: Systems with 8GB+ RAM automatically install advanced features during fresh setup—no prompts, fully automatic.
- **Smart Resource Management**: Pi Zero W/W2 automatically skip advanced tools due to hardware limitations.
- Server installs supported on AMD64/ARM64/ARMv7 with LAN-first networking; USB-gadget steps are skipped automatically off-Pi.
- On Pi, the only prompt is whether an e-Paper HAT is connected; everything else runs end-to-end automatically.
- Uses PiWheels on ARM, retries mirrors, and skips Pi-only steps on other hardware.

For **detailed information** about **installation** process go to [Install Guide](INSTALL.md)

### 🐝 Ragnar + Pwnagotchi Side by Side

Want to keep Ragnar online while occasionally hopping into Pwnagotchi mode? A bundled helper script plus new dashboard controls make the swap painless:

1. SSH into Ragnar and run the installer as root:
  ```bash
  cd /home/ragnar/Ragnar
  sudo ./scripts/install_pwnagotchi.sh
  ```
  - The script clones [pwnagotchiworking](https://github.com/PierreGode/pwnagotchiworking) into `/opt/pwnagotchi`, installs dependencies, writes `/etc/pwnagotchi/config.toml`, and drops a disabled `pwnagotchi.service`.
  - Re-running the installer is fast — it skips already-installed packages and pulls only new changes instead of re-cloning.
  - Progress is streamed to `/var/log/ragnar/pwnagotchi_install_<timestamp>.log` and mirrored in `data/pwnagotchi_status.json` for the UI.
2. Open the Ragnar web UI → **Config** tab → **Pwnagotchi Bridge**.
  - Click **Switch to Pwnagotchi** to hand off the systemd services. The button turns into a **Go to Pwnagotchi Portal** link (`http://<ip>:8080`) while the swap is in progress.

**Requirements for Pwnagotchi mode:**
- A USB WiFi adapter (wlan1) that supports monitor mode — pwnagotchi needs this for WiFi handshake capture. Without it, the installer defaults to `wlan1` and pwnagotchi will wait until one is plugged in.
- Waveshare 2.13" e-Paper HAT V4 for the pwnagotchi face display.

**Pwnagotchi web UI:** After swapping, the Pwnagotchi dashboard is at `http://<same-ip>:8080` with default credentials `ragnar` / `ragnar`.

**What the installer configures automatically:**
- Monitor mode scripts (`/usr/bin/monstart`, `/usr/bin/monstop`)
- e-Paper display type (`waveshare213_v4`) and rotation
- Web UI enabled on port 8080
- Pwngrid disabled (no-op shim to avoid log spam)
- RSA keys, log directories, bettercap integration

**Swapping via PiSugar 3 button:** If you have a PiSugar 3 battery attached, you can swap between Ragnar and Pwnagotchi with a physical button press — no web UI or SSH needed:

| Button Action | While Ragnar is running | While Pwnagotchi is running |
|---------------|------------------------|---------------------------|
| Single tap | Toggle manual mode (pause/resume scanning) | — |
| Double tap | Switch to Pwnagotchi | Switch to Ragnar |
| Long press | Switch to Pwnagotchi | Switch to Ragnar |

The PiSugar listener starts automatically on both sides. A 10-second cooldown prevents accidental double triggers. If PiSugar is not connected, the listener is silently disabled.

**Static IP recommended:** When switching between Ragnar and Pwnagotchi, the WiFi connection may briefly drop and reconnect with a different DHCP IP. To keep the same IP across swaps, set a static IP on wlan0:

```bash
# Replace with your network name, desired IP, gateway, and DNS
sudo nmcli con mod "YOUR_WIFI_SSID" ipv4.method manual \
  ipv4.addresses "192.168.1.211/24" \
  ipv4.gateway "192.168.1.1" \
  ipv4.dns "192.168.1.1"
sudo nmcli con up "YOUR_WIFI_SSID"
```

This only affects wlan0 (WiFi/web access). The monitor interface (wlan1/mon0) used by Pwnagotchi is not changed. Alternatively, set a DHCP reservation for the Pi's MAC address on your router.

**Service recovery:** If Ragnar doesn't start after a reboot or pwnagotchi gets stuck, run:

```bash
sudo /home/ragnar/Ragnar/scripts/fix_services.sh
```

This stops pwnagotchi, ensures ragnar.service is enabled, and resets the dashboard status.

### 🍍 WiFi Pineapple Pager

Ragnar can be deployed to the **WiFi Pineapple Pager** as a native payload with full-color LCD display, button controls, and LED status indicators. This brings autonomous network reconnaissance to a pocket-sized form factor.

**Features on Pager:**
- Full-color 480x222 LCD with Viking-themed status display
- Physical button controls (navigate menus, pause/resume, adjust brightness)
- LED indicators showing scan status (blue=idle, cyan=scanning, red=brute force, yellow=stealing)
- Graphical startup menu with interface selection and Web UI toggle
- Auto-dim screen to save battery
- Payload handoff support (switch between Ragnar and other Pager payloads)
- Web interface at `http://<pager-ip>:8000` when enabled

**Installation:**

Option A — From the main installer (select option 3):
```bash
sudo ./install_ragnar.sh
# Choose: 3. Install on WiFi Pineapple Pager
# Enter Pager IP (default: 172.16.42.1)
```

Option B — Direct deployment:
```bash
./install_pineapple_pager.sh [pager-ip]
```

**Requirements:**
- WiFi Pineapple Pager with firmware 1.0.7+
- PAGERCTL payload installed (provides `libpagerctl.so`)
- Python3 + nmap on the Pager (auto-installed on first run)
- SSH access to the Pager
- Bundled Python libraries from [pineapple_pager_bjorn](https://github.com/brAinphreAk/pineapple_pager_bjorn) (copied automatically if cloned alongside Ragnar)

**Usage on Pager:**
1. Launch from Pager menu: **Reconnaissance > PagerRagnar**
2. Press **GREEN** to confirm the splash screen
3. Select network interface and toggle Web UI on/off
4. Press **GREEN** on "Start Ragnar" to begin scanning
5. Press **RED** while running to open the pause menu (brightness control, main menu, exit)

## ⚡ Quick Start


**Quick Installation**: you can use the fastest way to install **Ragnar** [Getting Started](#-getting-started)


**Access Ragnar:**
- **Main Dashboard**: `http://<ragnar-ip>:8000` - Modern web interface with real-time updates
- **WiFi Portal**: `http://192.168.4.1/portal` - Mobile-friendly WiFi configuration (when in AP mode)
- **E-Paper Display**: Shows current status, IP address (.211), targets, vulnerabilities, and credentials

All discovered data is automatically organized in the `data/output/` directory, viewable through both the e-Paper display (as indicators) and web interface. Ragnar works tirelessly, expanding its network knowledge base and growing stronger with each discovery.

No constant monitoring needed - just deploy and let Ragnar do what it does best: hunt for vulnerabilities.

🔧 Expand Ragnar's Arsenal!
Ragnar is designed to be a community-driven weapon forge. Create and share your own attack modules!

> [!IMPORTANT]  
> **For educational use only!**

> Ragnar includes a built-in kill switch endpoint (`/api/kill`) that completely wipes all databases, logs, This ensures no sensitive data remains after demonstrations or training sessions.
> If Ragnar is to be found without permission in a network anyone kan completely wipe all databases + delete the entire repository rendering Ragnar dead.
> **📖 Full Documentation:** See [kill switch doc](KILL_SWITCH.md) for complete usage instructions and safety guidelines.
>
> **🔒 Authentication:** Ragnar supports optional hardware-bound login with full database encryption at rest. See [Security & Authentication](SECURITY.md).


⚠️ **For educational and authorized testing purposes only** ⚠️

## 🖥️ Server Mode: Advanced Features (8GB+ RAM)

When deployed on capable hardware (Debian-based systems with 8GB+ RAM), Ragnar automatically unlocks advanced security testing capabilities:

> **✅ Fresh Installations (AUTOMATIC):**
> The main `install_ragnar.sh` installer automatically detects systems with 8GB+ RAM and installs advanced tools during setup. **No user interaction required.** Pi Zero W/W2 are automatically excluded due to resource constraints.
>
> **⚠️ Existing Installations:**
> If you already have Ragnar running and want to enable these advanced features, you **must** run the advanced tools installer:
> ```bash
> cd /home/ragnar/Ragnar
> sudo ./install_advanced_tools.sh
> sudo systemctl restart ragnar
> ```

### 🔍 Real-Time Traffic Analysis
- **Live Packet Capture**: Monitor network traffic in real-time using tcpdump and tshark
- **Connection Tracking**: Track all TCP/UDP connections with detailed statistics
- **Protocol Analysis**: Deep inspection of HTTP, DNS, SMB, SSH, and other protocols
- **Bandwidth Monitoring**: Per-host bandwidth usage, top talkers, and connection patterns
- **Security Risk Scoring**: Automated risk assessment based on alerts and suspicious activity
- **Anomaly Detection**: Identify suspicious traffic patterns, port scans, and potential C2 beacons
- **DNS Query Logging**: Track all DNS lookups for threat intelligence correlation
- **Port Activity Monitoring**: Real-time port usage analysis across all hosts

### 🛡️ Advanced Vulnerability Scanning
- **OWASP ZAP Full Scan**: Spider + AJAX spider + active scan with automatic browser detection (Chrome/Chromium/Firefox)
- **Authenticated Scanning**: 8 authentication types for scanning protected applications:
  - Form-based login, HTTP Basic, OAuth2 Browser-Based (Microsoft/Azure AD), OAuth2 Client Credentials, Bearer Token, API Key, Cookie, Script-based
- **Live Scan Logs**: Real-time terminal-style log panel showing scan progress, phase transitions, and findings as they happen
- **Live Progress Tracking**: Auto-polling scan status with animated progress bar
- **Nuclei Templates**: Automated scanning with 5000+ vulnerability templates from ProjectDiscovery
- **Nikto Web Scanning**: Comprehensive web server vulnerability assessment
- **SQLMap Integration**: Automated SQL injection detection and exploitation
- **Parallel Scanning**: Multi-threaded vulnerability assessment for faster results
- **CVE Correlation**: Automatic correlation with NVD, CISA KEV, and threat intelligence feeds
- **Exploit Suggestions**: AI-powered recommendations for vulnerability exploitation paths
- **Web and API Scan Modes**: Scan traditional web apps or API endpoints with OpenAPI spec import

### 📊 Enhanced Web Interface
Server mode features are seamlessly integrated into the modern web dashboard at `http://<ragnar-ip>:8000`:
- **Traffic Analysis Tab**: Real-time packet capture visualization, bandwidth charts, top talkers, and security risk scoring
- **Advanced Vuln Tab**: Scan management with live progress, inline findings, live log viewer, severity breakdown, and auth status badges
- **Resource Monitor**: System resource usage and performance metrics
- **Threat Intelligence**: Multi-source threat correlation with actionable insights

### 🚀 Performance Benefits
- **Parallel Operations**: Run multiple scans and analyses simultaneously
- **Large Dictionary Support**: Use comprehensive wordlists for brute-force attacks
- **Extended Scanning**: Deeper port scans and more thorough vulnerability checks
- **Local AI Integration**: Optional on-device LLM support for offline analysis

### 📦 Installing Advanced Tools

**For fresh installations**: If your system has 8GB+ RAM and is not a Pi Zero, the main installer will automatically offer to install advanced tools.

**For existing Ragnar installations**, these advanced features require the separate installer:

```bash
cd /home/ragnar/Ragnar
sudo ./install_advanced_tools.sh
```

This script installs:
- **Traffic Analysis**: tcpdump, tshark, ngrep, iftop, nethogs
- **Vulnerability Scanners**: Nuclei, Nikto, SQLMap, WhatWeb
- **Web App Security**: OWASP ZAP (requires Java)
- **Nmap Scripts**: vulners.nse, vulscan database

**Pi Zero W/W2**: Advanced tools are not recommended due to limited CPU and RAM. The installer automatically skips resource-intensive tools on Pi Zero hardware.

After installation, restart Ragnar:
```bash
sudo systemctl restart ragnar
```

Ragnar will automatically detect available tools and enable corresponding features in the web interface.

## 🤝 Contributing

The project welcomes contributions in:

- New attack modules.
- Bug fixes.
- Documentation.
- Feature improvements.

For **detailed information** about **contributing** process go to [Contributing Docs](CONTRIBUTING.md), [Code Of Conduct](CODE_OF_CONDUCT.md) and [Development Guide](DEVELOPMENT.md).

## 📫 Contact

- **Report Issues**: Via GitHub.
- **Guidelines**:
  - Follow ethical guidelines.
  - Document reproduction steps.
  - Provide logs and context.

- **Author**: PierreGode
- **GitHub**: [PierreGode/Ragnar](https://github.com/PierreGode/Ragnar)

---

## 📜 License

2025 - Ragnar is distributed under the MIT License. For more details, please refer to the [LICENSE](LICENSE) file included in this repository.
