#!/usr/bin/env python3
"""
Pushover Notification Service for Ragnar
Sends push notifications via the Pushover API for security events.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


class PushoverService:
    """Lightweight wrapper around the Pushover HTTP API."""

    def __init__(self, shared_data):
        self.shared_data = shared_data
        self._lock = threading.Lock()
        # Tracks already-notified items to avoid spamming
        self._notified_devices = set()   # set of IPs
        self._notified_vulns = set()     # set of (ip, cve) tuples
        self._notified_creds = 0         # last known cred count
        self._last_send_ts = 0.0         # rate-limit: min 2 s between sends

    # ------------------------------------------------------------------
    # Key helpers (reads from .env via EnvManager)
    # ------------------------------------------------------------------

    def _get_keys(self):
        """Return (user_key, api_token) or (None, None) if not configured."""
        try:
            from env_manager import EnvManager
            em = EnvManager()
            user_key = em.get_env_key("RAGNAR_PUSHOVER_USER_KEY")
            api_token = em.get_env_key("RAGNAR_PUSHOVER_API_TOKEN")
            return user_key, api_token
        except Exception as e:
            logger.debug(f"Pushover key lookup failed: {e}")
            return None, None

    def is_configured(self):
        """Return True when both Pushover keys are present."""
        user_key, api_token = self._get_keys()
        return bool(user_key and api_token)

    def is_enabled(self):
        """Return True when Pushover is both configured and enabled in config."""
        return self.shared_data.config.get("pushover_enabled", False) and self.is_configured()

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    def send(self, message, title="Ragnar", priority=0, sound="pushover"):
        """Send a Pushover notification. Returns dict with success/message."""
        user_key, api_token = self._get_keys()
        if not user_key or not api_token:
            return {"success": False, "message": "Pushover keys not configured"}

        # Simple rate-limit (2 s)
        with self._lock:
            now = time.time()
            elapsed = now - self._last_send_ts
            if elapsed < 2.0:
                time.sleep(2.0 - elapsed)
            self._last_send_ts = time.time()

        try:
            import urllib.request
            import urllib.parse
            import json

            payload = urllib.parse.urlencode({
                "token": api_token,
                "user": user_key,
                "message": message,
                "title": title,
                "priority": priority,
                "sound": sound,
            }).encode("utf-8")

            req = urllib.request.Request(PUSHOVER_API_URL, data=payload, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("status") == 1:
                    logger.info(f"Pushover notification sent: {title}")
                    return {"success": True, "message": "Notification sent"}
                else:
                    err = body.get("errors", ["Unknown error"])
                    logger.warning(f"Pushover API error: {err}")
                    return {"success": False, "message": f"Pushover error: {err}"}

        except Exception as e:
            logger.error(f"Pushover send failed: {e}")
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Event helpers (called from webapp update loop)
    # ------------------------------------------------------------------

    def notify_new_devices(self, new_ips):
        """Notify about newly discovered devices (deduped)."""
        if not self.is_enabled():
            return
        if not self.shared_data.config.get("pushover_notify_new_device", True):
            return
        truly_new = [ip for ip in new_ips if ip not in self._notified_devices]
        if not truly_new:
            return
        self._notified_devices.update(truly_new)
        count = len(truly_new)
        ip_list = ", ".join(truly_new[:5])
        suffix = f" (+{count - 5} more)" if count > 5 else ""
        msg = f"⚔️ {count} new device(s) discovered on the network:\n{ip_list}{suffix}"
        threading.Thread(target=self.send, args=(msg, "Ragnar — New Device"), daemon=True).start()

    def notify_device_lost(self, lost_ips):
        """Notify when devices go offline."""
        if not self.is_enabled():
            return
        if not self.shared_data.config.get("pushover_notify_device_lost", False):
            return
        if not lost_ips:
            return
        count = len(lost_ips)
        ip_list = ", ".join(sorted(lost_ips)[:5])
        suffix = f" (+{count - 5} more)" if count > 5 else ""
        msg = f"🛡️ {count} device(s) went offline:\n{ip_list}{suffix}"
        threading.Thread(target=self.send, args=(msg, "Ragnar — Device Lost"), daemon=True).start()

    def notify_new_vulnerabilities(self, vuln_count, details=""):
        """Notify about newly discovered vulnerabilities."""
        if not self.is_enabled():
            return
        if not self.shared_data.config.get("pushover_notify_new_vulnerability", True):
            return
        if vuln_count <= 0:
            return
        msg = f"🔥 {vuln_count} new vulnerability/vulnerabilities found!"
        if details:
            msg += f"\n{details[:200]}"
        threading.Thread(target=self.send, args=(msg, "Ragnar — Vulnerability Alert", 1), daemon=True).start()

    def notify_new_credentials(self, new_count, total):
        """Notify when new credentials are captured."""
        if not self.is_enabled():
            return
        if not self.shared_data.config.get("pushover_notify_new_credential", True):
            return
        if new_count <= 0:
            return
        if total == self._notified_creds:
            return
        self._notified_creds = total
        msg = f"🗝️ {new_count} new credential(s) captured! (total: {total})"
        threading.Thread(target=self.send, args=(msg, "Ragnar — Credentials"), daemon=True).start()

    def notify_scan_complete(self, hosts, ports, vulns):
        """Notify when a full scan cycle completes."""
        if not self.is_enabled():
            return
        if not self.shared_data.config.get("pushover_notify_scan_complete", False):
            return
        msg = (
            f"📡 Scan cycle complete\n"
            f"Hosts: {hosts}  |  Ports: {ports}  |  Vulns: {vulns}"
        )
        threading.Thread(target=self.send, args=(msg, "Ragnar — Scan Complete"), daemon=True).start()
