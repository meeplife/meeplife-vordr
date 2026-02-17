#!/bin/bash
# Pierre Gode (Updated Installer - Debian 12/13 Compatible + Key Fix + pwngrid Disable)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATUS_FILE="$REPO_ROOT/data/pwnagotchi_status.json"
LOG_DIR="/var/log/ragnar"
LOG_FILE="$LOG_DIR/pwnagotchi_install_$(date +%Y%m%d_%H%M%S).log"
PWN_DIR="/opt/pwnagotchi"
PWN_REPO="https://github.com/PierreGode/pwnagotchiworking.git"
SERVICE_FILE="/etc/systemd/system/pwnagotchi.service"
CONFIG_DIR="/etc/pwnagotchi"
CONFIG_FILE="$CONFIG_DIR/config.toml"
TEMP_DIR="/home/ragnar/tmp_pwnagotchi_install"
MIN_SPACE_MB=300

mkdir -p "$LOG_DIR" "$REPO_ROOT/data" "$TEMP_DIR"

export TMPDIR="$TEMP_DIR"
export TEMP="$TEMP_DIR"
export TMP="$TEMP_DIR"

touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

write_status() {
    local state="$1"
    local message="$2"
    local phase="$3"
    cat >"$STATUS_FILE" <<EOF
{
    "state": "${state}",
    "message": "${message}",
    "phase": "${phase}",
    "timestamp": "$(date -Iseconds)",
    "log_file": "${LOG_FILE}",
    "service_file": "${SERVICE_FILE}",
    "config_file": "${CONFIG_FILE}",
    "repo_dir": "${PWN_DIR}"
}
EOF
}

select_station_interface() {
    local attempt=0
    local max_attempts=5
    local is_interactive=false

    # Check if we're running in an interactive terminal
    if [[ -t 0 ]]; then
        is_interactive=true
    fi

    while true; do
        attempt=$((attempt + 1))
        mapfile -t wlan_ifaces < <(ls /sys/class/net 2>/dev/null | grep -E '^wlan[0-9]+' | sort || true)
        for iface in "${wlan_ifaces[@]}"; do
            if [[ "$iface" != "wlan0" ]]; then
                echo "$iface"
                return 0
            fi
        done
        echo "[WARN] No secondary wlan interface detected (attempt ${attempt}/${max_attempts})." >&2
        echo "[WARN] Connect a USB WiFi adapter (wlan1/wlan2...) for monitor mode." >&2

        # Non-interactive mode (GUI install): retry a few times then fail gracefully
        if [[ "$is_interactive" != true ]]; then
            if [[ $attempt -ge $max_attempts ]]; then
                echo "[ERROR] No secondary WiFi adapter found after ${max_attempts} attempts." >&2
                echo "[ERROR] Please connect a USB WiFi adapter and try again." >&2
                return 1
            fi
            echo "[INFO] Waiting 3 seconds before retry (attempt ${attempt}/${max_attempts})..." >&2
            sleep 3
            continue
        fi

        # Interactive mode (terminal install): prompt user
        read -rp "Press Enter to rescan or type 'abort' to cancel installation: " response || true
        if [[ "${response,,}" == "abort" ]]; then
            return 1
        fi
        sleep 2
    done
}

set_or_update_config_value() {
    local dotted_key="$1"
    local value="$2"
    # Use Python + tomlkit to safely update TOML table-style configs
    python3 -c "
import tomlkit, sys
key_path = '${dotted_key}'.split('.')
val = '${value}'
with open('${CONFIG_FILE}', 'r') as f:
    doc = tomlkit.parse(f.read())
d = doc
for k in key_path[:-1]:
    if k not in d:
        d[k] = tomlkit.table()
    d = d[k]
d[key_path[-1]] = val
with open('${CONFIG_FILE}', 'w') as f:
    f.write(tomlkit.dumps(doc))
" 2>/dev/null || {
        # Fallback: append as flat dotted key if tomlkit unavailable
        echo "$dotted_key = \"$value\"" >> "$CONFIG_FILE"
    }
}

install_monitor_scripts() {
    local station_if="$1"
    local monitor_if="$2"

    cat > /usr/bin/monstart <<EOF
#!/bin/bash
set -euo pipefail

STA_IF="$station_if"
MON_IF="$monitor_if"

log() {
    echo "[monstart] \$*"
}

if ip link show "\$MON_IF" >/dev/null 2>&1; then
    ip link set "\$MON_IF" down >/dev/null 2>&1 || true
    iw "\$MON_IF" del >/dev/null 2>&1 || true
fi

ip link set "\$STA_IF" down >/dev/null 2>&1 || true
iw dev "\$STA_IF" set type managed >/dev/null 2>&1 || true
ip link set "\$STA_IF" up >/dev/null 2>&1 || true

if ! iw dev "\$STA_IF" interface add "\$MON_IF" type monitor >/dev/null 2>&1; then
    log "Failed to create monitor interface from \$STA_IF"
    exit 1
fi

ip link set "\$MON_IF" up >/dev/null 2>&1 || true
log "Monitor interface \$MON_IF ready (parent: \$STA_IF)"
exit 0
EOF

    cat > /usr/bin/monstop <<EOF
#!/bin/bash
set -euo pipefail

STA_IF="$station_if"
MON_IF="$monitor_if"

if ip link show "\$MON_IF" >/dev/null 2>&1; then
    ip link set "\$MON_IF" down >/dev/null 2>&1 || true
    iw "\$MON_IF" del >/dev/null 2>&1 || true
fi

ip link set "\$STA_IF" up >/dev/null 2>&1 || true
exit 0
EOF

    chmod 755 /usr/bin/monstart /usr/bin/monstop
    chown root:root /usr/bin/monstart /usr/bin/monstop
}

trap 'write_status "error" "Installation failed (line ${LINENO}). Check ${LOG_FILE}." "error"' ERR

# -------------------------------------------------------------------
# PRECHECK
# -------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    echo "This installer must be run as root."
    exit 1
fi

# Block installation when Ragnar is running without an e-paper display
HEADLESS_DETECTED=false
if pgrep -f "headlessRagnar.py" >/dev/null 2>&1; then
    HEADLESS_DETECTED=true
else
    if systemctl cat ragnar.service 2>/dev/null | grep -q "headlessRagnar.py"; then
        HEADLESS_DETECTED=true
    fi
fi

if [[ "$HEADLESS_DETECTED" == true ]]; then
    BLOCK_MSG="Pwnagotchi requires an e-paper display, but Ragnar is running in Headless mode. Installation is disabled."
    echo "[ERROR] ${BLOCK_MSG}"
    write_status "error" "$BLOCK_MSG" "preflight"
    exit 1
fi

write_status "installing" "Starting Pwnagotchi installation" "preflight"
echo "[INFO] Beginning Pwnagotchi installation..."

echo "[INFO] Checking disk space in $TEMP_DIR..."
available_space=$(df -m "$TEMP_DIR" | awk 'NR==2 {print $4}')
echo "[INFO] Available disk space: ${available_space} MB"

if [[ $available_space -lt $MIN_SPACE_MB ]]; then
    echo "[ERROR] Insufficient disk space (${available_space} MB). Need at least ${MIN_SPACE_MB} MB."
    write_status "error" "Insufficient disk space. Free up space and retry." "preflight"
    exit 1
fi

write_status "installing" "Updating package lists" "apt_update"
echo "[INFO] Updating apt repositories"
apt-get update -y

# -------------------------------------------------------------------
# SYSTEM PACKAGES
# -------------------------------------------------------------------
packages=(
    git
    python3
    python3-pip
    python3-setuptools
    python3-dev
    python3-venv
    libpcap-dev
    libffi-dev
    libssl-dev
    libcap2-bin
    python3-smbus
    i2c-tools
    libglib2.0-dev
    pkg-config
    meson
)

optional_packages=(
    bettercap
    hcxdumptool
    hcxtools
    libopenblas-dev
    liblapack-dev
)

write_status "installing" "Installing required system packages" "apt_required"
echo "[INFO] Installing required packages..."
apt-get install -y "${packages[@]}"

write_status "installing" "Installing optional wireless tools" "apt_optional"
echo "[INFO] Installing optional wireless tools in one batch..."
if ! apt-get install -y "${optional_packages[@]}"; then
    echo "[WARN] Optional wireless bundle had installation issues. Continuing with required packages only."
fi

write_status "installing" "System packages installed" "dependencies"

# -------------------------------------------------------------------
# CLONE REPOSITORY
# -------------------------------------------------------------------
write_status "installing" "Cloning Pwnagotchi repository" "clone"
echo "[INFO] Cloning Pwnagotchi repository to ${PWN_DIR}"
rm -rf "$PWN_DIR"
# Use shallow clone for faster download
git clone --depth 1 "$PWN_REPO" "$PWN_DIR"

write_status "installing" "Installing Pwnagotchi from source" "python"
cd "$PWN_DIR"

# -------------------------------------------------------------------
# PIP + INSTALL
# -------------------------------------------------------------------
write_status "installing" "Upgrading pip" "pip"
echo "[INFO] Upgrading pip..."
python3 -m pip install --upgrade --break-system-packages pip || echo "[WARN] pip upgrade skipped"

write_status "installing" "Installing Pwnagotchi package and dependencies" "python_install"
echo "[INFO] Installing Pwnagotchi package (editable mode via pyproject.toml)..."
# pwnagotchiworking uses pyproject.toml — pip install -e . handles all deps
python3 -m pip install \
    --break-system-packages \
    --use-pep517 \
    -e .

# -------------------------------------------------------------------
# VALIDATE + FIX /etc/pwnagotchi
# -------------------------------------------------------------------
write_status "installing" "Configuring Pwnagotchi directories" "config_dirs"
echo "[INFO] Validating /etc/pwnagotchi directory..."

mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"
chown root:root "$CONFIG_DIR"

write_status "installing" "Detecting WiFi interfaces" "interface_detect"
STATION_IFACE="${PWN_DATA_IFACE:-}"
if [[ -z "$STATION_IFACE" ]]; then
    if ! STATION_IFACE=$(select_station_interface); then
        STATION_IFACE="wlan1"
        echo "[WARN] No USB WiFi adapter detected. Defaulting to '${STATION_IFACE}'." >&2
        echo "[WARN] Pwnagotchi will not work until a USB WiFi adapter is connected." >&2
        echo "[WARN] Continuing installation so everything is ready when the adapter is plugged in." >&2
        write_status "installing" "No WiFi adapter found - defaulting to wlan1. Connect adapter before starting." "interface_warn"
    fi
fi
MONITOR_IFACE_NAME="${PWN_MON_IFACE:-mon0}"
echo "[INFO] Using managed iface: ${STATION_IFACE} (monitor alias: ${MONITOR_IFACE_NAME})"

write_status "installing" "Installing monitor mode scripts" "monitor_scripts"
install_monitor_scripts "$STATION_IFACE" "$MONITOR_IFACE_NAME"

# -------------------------------------------------------------------
# RSA KEY VALIDATION + AUTO-GENERATION
# -------------------------------------------------------------------
write_status "installing" "Setting up RSA keys" "rsa_keys"
if [[ ! -f "$CONFIG_DIR/id_rsa" ]]; then
    echo "[INFO] Generating new RSA keypair for Pwnagotchi..."
    ssh-keygen -t rsa -b 2048 -f "$CONFIG_DIR/id_rsa" -N ""
else
    echo "[INFO] RSA private key already exists — skipping generation."
fi

chmod 600 "$CONFIG_DIR/id_rsa"
chmod 644 "$CONFIG_DIR/id_rsa.pub"

# -------------------------------------------------------------------
# CONFIG FILE SETUP
# -------------------------------------------------------------------
write_status "installing" "Creating configuration files" "config_files"
if [[ ! -f "$CONFIG_FILE" ]]; then
    cat >"$CONFIG_FILE" <<EOF
# Ragnar-managed Pwnagotchi user config (pwnagotchiworking / noai branch)
# Overrides values from default.toml

[main]
name = "RagnarPwn"
confd = "/etc/pwnagotchi/conf.d"
custom_plugins = "/etc/pwnagotchi/custom_plugins"
iface = "${STATION_IFACE}"
mon_iface = "${MONITOR_IFACE_NAME}"
mon_start_cmd = "/usr/bin/monstart"
mon_stop_cmd = "/usr/bin/monstop"

[ui.display]
enabled = false

[ui.web]
enabled = true
username = "ragnar"
password = "ragnar"

[ui.font]
name = "DejaVuSansMono"

[main.plugins.grid]
enabled = false
EOF
    echo "[INFO] Created default config at ${CONFIG_FILE}"
else
    set_or_update_config_value "main.iface" "${STATION_IFACE}"
    set_or_update_config_value "main.mon_iface" "${MONITOR_IFACE_NAME}"
    set_or_update_config_value "main.mon_start_cmd" "/usr/bin/monstart"
    set_or_update_config_value "main.mon_stop_cmd" "/usr/bin/monstop"
fi

mkdir -p "$CONFIG_DIR/conf.d" "$CONFIG_DIR/custom_plugins"

# -------------------------------------------------------------------
# DISABLE PWNGIRD EXECUTION (REMOVE LOG SPAM)
# -------------------------------------------------------------------
echo "[INFO] Installing pwngrid no-op shim..."

if [[ ! -f "/usr/local/bin/pwngrid" ]]; then
    cat >/usr/local/bin/pwngrid <<'EOF'
#!/bin/bash
# Dummy pwngrid replacement to avoid log spam
exit 0
EOF
    chmod +x /usr/local/bin/pwngrid
    echo "[INFO] pwngrid shim installed."
else
    echo "[INFO] pwngrid shim already exists — skipping."
fi

# -------------------------------------------------------------------
# ENSURE LAUNCHER WRAPPER EXISTS
# -------------------------------------------------------------------
echo "[INFO] Ensuring /usr/bin/pwnagotchi-launcher wrapper exists..."
launcher_candidates=(
    "$(command -v pwnagotchi 2>/dev/null)"
    "$(command -v pwnagotchi-launcher 2>/dev/null)"
    "/usr/local/bin/pwnagotchi"
    "/usr/local/bin/pwnagotchi-launcher"
)

launcher_target=""
for candidate in "${launcher_candidates[@]}"; do
    if [[ -n "$candidate" && -x "$candidate" && "$candidate" != "/usr/bin/pwnagotchi-launcher" ]]; then
        launcher_target="$candidate"
        break
    fi
done

if [[ -n "$launcher_target" ]]; then
    cat > /usr/bin/pwnagotchi-launcher <<EOF
#!/bin/bash
exec ${launcher_target} "\$@"
EOF
    chmod 755 /usr/bin/pwnagotchi-launcher
    chown root:root /usr/bin/pwnagotchi-launcher
    echo "[INFO] Launcher wrapper points to ${launcher_target}"
else
    echo "[WARN] Could not determine pwnagotchi binary path; launcher wrapper not updated."
fi

# -------------------------------------------------------------------
# SYSTEMD SERVICE SETUP
# -------------------------------------------------------------------
write_status "installing" "Setting up systemd service" "systemd"
cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=Pwnagotchi Mode Service
After=multi-user.target network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/pwnagotchi
WorkingDirectory=${PWN_DIR}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_FILE"
systemctl daemon-reload
systemctl disable pwnagotchi >/dev/null 2>&1 || true
systemctl stop pwnagotchi >/dev/null 2>&1 || true

# -------------------------------------------------------------------
# BOOT-TIME MIGRATION SERVICE
# -------------------------------------------------------------------
write_status "installing" "Setting up migration service" "migration_service"
MIGRATE_SCRIPT="$REPO_ROOT/scripts/migrate_pwnagotchi.sh"
MIGRATE_SERVICE="/etc/systemd/system/ragnar-pwn-migrate.service"

if [[ -f "$MIGRATE_SCRIPT" ]]; then
    chmod 755 "$MIGRATE_SCRIPT"

    cat >"$MIGRATE_SERVICE" <<EOF
[Unit]
Description=Ragnar Pwnagotchi Migration Check
After=local-fs.target network-online.target
Before=pwnagotchi.service ragnar.service
ConditionPathExists=/opt/pwnagotchi

[Service]
Type=oneshot
ExecStart=${MIGRATE_SCRIPT}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    chmod 644 "$MIGRATE_SERVICE"
    systemctl daemon-reload
    systemctl enable ragnar-pwn-migrate >/dev/null 2>&1 || true
    echo "[INFO] Boot-time migration service installed and enabled."

    # Write marker since we just did a fresh install of the correct version
    mkdir -p /var/lib/ragnar
    date -Iseconds > /var/lib/ragnar/.pwn_migrated
else
    echo "[WARN] migrate_pwnagotchi.sh not found; skipping migration service setup."
fi

# -------------------------------------------------------------------
# BETTERCAP SERVICE SYNC
# -------------------------------------------------------------------
if [[ -f "/usr/bin/bettercap-launcher" ]]; then
    echo "[INFO] Ensuring bettercap launcher permissions..."
    chmod 755 /usr/bin/bettercap-launcher
else
    echo "[WARN] /usr/bin/bettercap-launcher not found; skipping chmod."
fi

if systemctl list-unit-files | grep -q '^bettercap\.service'; then
    echo "[INFO] Reloading systemd units and restarting bettercap..."
    systemctl daemon-reload
    systemctl restart bettercap
else
    echo "[WARN] bettercap.service not detected; skipping restart."
fi

# -------------------------------------------------------------------
# CLEANUP
# -------------------------------------------------------------------
write_status "installing" "Cleaning up temporary files" "cleanup"
echo "[INFO] Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

write_status "installed" "Pwnagotchi installed successfully. Use Ragnar dashboard to launch." "complete"
echo "[INFO] Installation complete. Service disabled until manually started."
