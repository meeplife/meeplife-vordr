#!/bin/bash
# Title: Ragnar
# Description: Autonomous network reconnaissance and security scanning tool for WiFi Pineapple Pager - Network scanning, vulnerability assessment, brute force, and data exfiltration with Viking personality
# Author: PierreGode / Ragnar Project
# Version: 1.0
# Category: Reconnaissance
# Library: libpagerctl.so (pagerctl)

# Payload directory (standard Pager installation path)
PAYLOAD_DIR="/root/payloads/user/reconnaissance/pager_ragnar"
DATA_DIR="$PAYLOAD_DIR/data"

cd "$PAYLOAD_DIR" || {
    LOG "red" "ERROR: $PAYLOAD_DIR not found"
    exit 1
}

#
# Find and setup pagerctl dependencies (libpagerctl.so + pagerctl.py)
#
PAGERCTL_FOUND=false
PAGERCTL_SEARCH_PATHS=(
    "$PAYLOAD_DIR/lib"
    "$PAYLOAD_DIR"
    "/root/lib"
    "/mmc/root/payloads/user/utilities/PAGERCTL"
)

for dir in "${PAGERCTL_SEARCH_PATHS[@]}"; do
    if [ -f "$dir/libpagerctl.so" ]; then
        PAGERCTL_DIR="$dir"
        PAGERCTL_FOUND=true
        break
    fi
done

if [ "$PAGERCTL_FOUND" = false ]; then
    LOG ""
    LOG "red" "=== MISSING DEPENDENCY ==="
    LOG ""
    LOG "red" "libpagerctl.so not found!"
    LOG ""
    LOG "Searched:"
    for dir in "${PAGERCTL_SEARCH_PATHS[@]}"; do
        LOG "  $dir"
    done
    LOG ""
    LOG "Install PAGERCTL payload or copy files to:"
    LOG "  $PAYLOAD_DIR/lib/"
    LOG ""
    LOG "Press any button to exit..."
    WAIT_FOR_INPUT >/dev/null 2>&1
    exit 1
fi

# If pagerctl files aren't in our lib dir, copy them there
if [ "$PAGERCTL_DIR" != "$PAYLOAD_DIR/lib" ] && [ "$PAGERCTL_DIR" != "$PAYLOAD_DIR" ]; then
    mkdir -p "$PAYLOAD_DIR/lib" 2>/dev/null
    cp "$PAGERCTL_DIR/libpagerctl.so" "$PAYLOAD_DIR/lib/" 2>/dev/null
    [ -f "$PAGERCTL_DIR/pagerctl.py" ] && cp "$PAGERCTL_DIR/pagerctl.py" "$PAYLOAD_DIR/lib/" 2>/dev/null
    LOG "green" "Copied pagerctl from $PAGERCTL_DIR"
fi

#
# Setup local paths for bundled binaries and libraries
#
export PATH="/mmc/usr/bin:$PAYLOAD_DIR/bin:$PATH"
export PYTHONPATH="$PAYLOAD_DIR/lib:$PAYLOAD_DIR:$PYTHONPATH"
export LD_LIBRARY_PATH="/root/lib:/mmc/usr/lib:$PAYLOAD_DIR/lib:$PAYLOAD_DIR:$LD_LIBRARY_PATH"
export CRYPTOGRAPHY_OPENSSL_NO_LEGACY=1
export RAGNAR_PAGER_MODE=1

#
# Check for Python3 and python3-ctypes
#
NEED_PYTHON=false
NEED_CTYPES=false

if ! command -v python3 >/dev/null 2>&1; then
    NEED_PYTHON=true
    NEED_CTYPES=true
elif ! python3 -c "import ctypes" 2>/dev/null; then
    NEED_CTYPES=true
fi

if [ "$NEED_PYTHON" = true ] || [ "$NEED_CTYPES" = true ]; then
    LOG ""
    LOG "red" "=== MISSING REQUIREMENT ==="
    LOG ""
    if [ "$NEED_PYTHON" = true ]; then
        LOG "Python3 is required to run Ragnar."
    else
        LOG "Python3-ctypes is required to run Ragnar."
    fi
    LOG "All other dependencies are bundled."
    LOG ""
    LOG "green" "GREEN = Install dependencies (requires internet)"
    LOG "red" "RED   = Exit"
    LOG ""

    while true; do
        BUTTON=$(WAIT_FOR_INPUT 2>/dev/null)
        case "$BUTTON" in
            "GREEN"|"A")
                LOG ""
                LOG "Updating package lists..."
                opkg update 2>&1 | while IFS= read -r line; do LOG "  $line"; done
                LOG ""
                LOG "Installing Python3 + ctypes to MMC..."
                opkg -d mmc install python3 python3-ctypes 2>&1 | while IFS= read -r line; do LOG "  $line"; done
                LOG ""
                if command -v python3 >/dev/null 2>&1 && python3 -c "import ctypes" 2>/dev/null; then
                    LOG "green" "Python3 installed successfully!"
                    sleep 1
                else
                    LOG "red" "Failed to install Python3"
                    LOG "red" "Check internet connection and try again."
                    LOG ""
                    LOG "Press any button to exit..."
                    WAIT_FOR_INPUT >/dev/null 2>&1
                    exit 1
                fi
                break
                ;;
            "RED"|"B")
                LOG "Exiting."
                exit 0
                ;;
        esac
    done
fi

#
# Check nmap dependency
#
check_dependencies() {
    LOG ""
    LOG "Checking dependencies..."

    if ! command -v nmap >/dev/null 2>&1; then
        LOG ""
        LOG "red" "nmap not found. Installing..."
        opkg update 2>&1 | while IFS= read -r line; do LOG "  $line"; done
        opkg -d mmc install nmap 2>&1 | while IFS= read -r line; do LOG "  $line"; done

        if ! command -v nmap >/dev/null 2>&1; then
            LOG "red" "ERROR: nmap installation failed!"
            LOG "Press any button to exit..."
            WAIT_FOR_INPUT >/dev/null 2>&1
            exit 1
        fi
    fi

    LOG "green" "All dependencies found!"
}

# ============================================================
# CLEANUP
# ============================================================

cleanup() {
    # Re-register and start pager service (undoes the procd deregister below)
    /etc/init.d/pineapplepager start 2>/dev/null
}

trap cleanup EXIT

# ============================================================
# MAIN
# ============================================================

check_dependencies

# Check network connectivity
HAS_NETWORK=false
while IFS= read -r line; do
    if [[ "$line" =~ inet\ ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
        IP="${BASH_REMATCH[1]}"
        if [[ "$IP" != "127.0.0.1" ]]; then
            HAS_NETWORK=true
            break
        fi
    fi
done < <(ip addr 2>/dev/null)

if [ "$HAS_NETWORK" = false ]; then
    LOG ""
    LOG "red" "=== NO NETWORK CONNECTED ==="
    LOG ""
    LOG "Ragnar requires a network connection to scan."
    LOG "Please connect to a network first:"
    LOG "  - WiFi client mode (wlan0cli)"
    LOG "  - Ethernet/USB (br-lan)"
    LOG ""
    LOG "Press any button to exit..."
    WAIT_FOR_INPUT >/dev/null 2>&1
    exit 1
fi

# Show splash screen
LOG ""
LOG "green" "Ragnar"
LOG "cyan" "https://github.com/PierreGode/Ragnar"
LOG ""
LOG "yellow" "Features:"
LOG "cyan" "  - Automated network reconnaissance"
LOG "cyan" "  - Port scanning with nmap"
LOG "cyan" "  - SSH/SMB/FTP/Telnet/RDP/SQL brute force"
LOG "cyan" "  - File stealing and data exfiltration"
LOG "cyan" "  - Vulnerability scanning"
LOG "cyan" "  - Web UI for monitoring"
LOG ""
LOG "green" "GREEN = Start"
LOG "red" "RED = Exit"
LOG ""

while true; do
    BUTTON=$(WAIT_FOR_INPUT 2>/dev/null)
    case "$BUTTON" in
        "GREEN"|"A")
            break
            ;;
        "RED"|"B")
            LOG "Exiting."
            exit 0
            ;;
    esac
done

# Create data directory
mkdir -p "$DATA_DIR" 2>/dev/null

# Take exclusive LCD control from the Pineapple system.
# Two processes share the LCD:
#   pineapple  = main UI server (handles LCD, buttons, payloads)
#   pineapd    = PineAP WiFi daemon
#
# CRITICAL: Kill pineapple FIRST. If we only kill pineapd (as init.d stop does),
# the pineapple process detects the death and auto-restarts everything:
#   "[CRITICAL] [PINEAP] PineAPd not available, restarting service"
# This steals the LCD back from Ragnar within seconds.

LOG "Starting Ragnar..."

# Protect ourselves: pineapple may signal its process group on death
trap '' TERM HUP

# 1. Kill the main pineapple UI server first (prevents restart cascade)
killall -TERM pineapple 2>/dev/null
sleep 0.3

# 2. Kill the PineAP daemon
killall -TERM pineapd 2>/dev/null
sleep 0.3

# 3. Deregister service from procd to prevent auto-respawn
ubus call service delete '{"name":"pineapplepager"}' 2>/dev/null

# 4. Ensure both processes are fully dead (SIGKILL as fallback)
killall -KILL pineapple 2>/dev/null
killall -KILL pineapd 2>/dev/null
sleep 0.5

# Restore signal handling (cleanup trap still fires on EXIT)
trap cleanup EXIT

# Payload loop with handoff support
NEXT_PAYLOAD_FILE="$DATA_DIR/.next_payload"

while true; do
    cd "$PAYLOAD_DIR"
    python3 pager_menu.py
    EXIT_CODE=$?

    if [ "$EXIT_CODE" -eq 42 ] && [ -f "$NEXT_PAYLOAD_FILE" ]; then
        NEXT_SCRIPT=$(cat "$NEXT_PAYLOAD_FILE")
        rm -f "$NEXT_PAYLOAD_FILE"
        if [ -f "$NEXT_SCRIPT" ]; then
            bash "$NEXT_SCRIPT"
            [ $? -eq 42 ] && continue
        fi
    fi

    if [ "$EXIT_CODE" -eq 99 ]; then
        continue
    fi

    break
done

exit 0
