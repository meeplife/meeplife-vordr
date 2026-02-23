#!/usr/bin/env python3
"""
Pwnagotchi-side PiSugar button listener for swapping back to Ragnar.

This script runs alongside Pwnagotchi (started by the pwnagotchi.service).
When the PiSugar button is double-tapped or long-pressed, it stops Pwnagotchi
and bettercap services and starts the Ragnar service.

Installed to /usr/local/bin/ragnar-swap-button by the pwnagotchi installer.
Managed by ragnar-swap-button.service.
"""

import subprocess
import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format='[ragnar-swap] %(message)s')
log = logging.getLogger()

COOLDOWN = 10  # seconds between swap attempts


def swap_to_ragnar():
    """Stop Pwnagotchi/bettercap and start Ragnar."""
    log.info("Button triggered: swapping to Ragnar...")
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', 'pwnagotchi.service'], timeout=30)
        subprocess.run(['sudo', 'systemctl', 'stop', 'bettercap.service'], timeout=15)
        subprocess.run(['sudo', 'systemctl', 'start', 'ragnar.service'], timeout=30)
        log.info("Ragnar service started.")
    except Exception as e:
        log.error(f"Swap failed: {e}")


def main():
    try:
        from pisugar import connect_tcp, PiSugarServer
    except ImportError:
        log.error("pisugar package not installed. Run: pip3 install pisugar")
        sys.exit(1)

    # Connect to pisugar-server with retries
    server = None
    for attempt in range(5):
        try:
            conn, event_conn = connect_tcp('127.0.0.1')
            server = PiSugarServer(conn, event_conn)
            model = server.get_model()
            log.info(f"PiSugar connected: {model}")
            break
        except Exception as e:
            log.info(f"PiSugar not ready (attempt {attempt + 1}/5): {e}")
            time.sleep(5)

    if not server:
        log.error("PiSugar not available. Exiting.")
        sys.exit(1)

    last_swap = 0

    def on_swap():
        nonlocal last_swap
        now = time.time()
        if now - last_swap < COOLDOWN:
            return
        last_swap = now
        swap_to_ragnar()

    server.register_double_tap_handler(on_swap)
    server.register_long_tap_handler(on_swap)
    log.info("Listening for PiSugar button (double tap or long press = swap to Ragnar)")

    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopped.")


if __name__ == '__main__':
    main()
