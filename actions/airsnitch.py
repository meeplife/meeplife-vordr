#!/usr/bin/env python3
"""
AirSnitch Wi-Fi Client Isolation Testing Module for Ragnar

Tests whether a Wi-Fi network properly enforces client isolation using three attack vectors:
  - GTK Abuse: checks if clients share a group transient key
  - Gateway Bouncing: tests IP-layer isolation bypass via the gateway
  - Port Stealing: tests whether an attacker can intercept victim traffic

Source: https://github.com/vanhoefm/airsnitch

WARNING: Only run against networks you own or have explicit written permission to test.
"""

import os
import json
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

# Required attributes for Ragnar action framework
b_class = "AirSnitch"
b_module = "airsnitch"
b_status = "airsnitch_scan"
b_port = None   # Standalone – not tied to a specific port
b_parent = None

AIRSNITCH_REPO = "https://github.com/vanhoefm/airsnitch.git"
DEFAULT_TIMEOUT = 120  # seconds per test


class AirSnitchRunner:
    """
    Low-level wrapper around the airsnitch.py command-line tool.
    Handles installation, configuration, and execution.
    """

    def __init__(self, install_dir: str, logger: logging.Logger, log_file: Optional[Path] = None):
        self.install_dir = Path(install_dir)
        self.logger = logger
        # The main script lives in the research/ subdirectory of the modified hostap tree
        self.script = self.install_dir / "airsnitch" / "research" / "airsnitch.py"
        self.research_dir = self.script.parent
        self.install_log_file = log_file  # Path to write live install output
        self.run_log_file: Optional[Path] = None  # Path to write live test output

    # ------------------------------------------------------------------
    # Installation helpers
    # ------------------------------------------------------------------

    @property
    def wpa_supplicant_bin(self) -> Path:
        """Expected path of the custom-compiled wpa_supplicant binary.
        build.sh is run inside airsnitch/research/ so the binary ends up at
        install_dir/airsnitch/wpa_supplicant/wpa_supplicant (one level up from research/).
        """
        return self.research_dir.parent / "wpa_supplicant" / "wpa_supplicant"

    def is_installed(self) -> bool:
        """True only when both the research script AND compiled wpa_supplicant exist."""
        return self.script.exists() and self.wpa_supplicant_bin.exists()

    def _log(self, msg: str) -> None:
        """Write a message to both the Python logger and the live install log file."""
        self.logger.info(msg)
        if self.install_log_file:
            try:
                with open(self.install_log_file, "a") as fh:
                    fh.write(msg + "\n")
            except Exception:
                pass

    def _run_log(self, msg: str) -> None:
        """Write a message to both the Python logger and the live run log file."""
        self.logger.info(msg)
        if self.run_log_file:
            try:
                with open(self.run_log_file, "a") as fh:
                    fh.write(msg + "\n")
            except Exception:
                pass

    def get_run_log(self) -> str:
        """Return the current contents of the run log (empty string if none)."""
        if not self.run_log_file:
            return ""
        try:
            return Path(self.run_log_file).read_text()
        except Exception:
            return ""

    def _run_logged(self, cmd: list, cwd: Optional[str] = None, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a command and stream its output line-by-line to the install log."""
        self._log(f"$ {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        output_lines = []
        try:
            for line in proc.stdout:
                line = line.rstrip("\n")
                output_lines.append(line)
                self._log(line)
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            self._log("ERROR: command timed out")
        return subprocess.CompletedProcess(cmd, proc.returncode, "\n".join(output_lines), "")

    def _install_system_deps(self) -> bool:
        """Ensure build dependencies for hostapd/wpa_supplicant are present."""
        # Packages required to build wpa_supplicant and run AirSnitch
        pkgs = [
            "libnl-3-dev",
            "libnl-genl-3-dev",
            "libnl-route-3-dev",
            "libssl-dev",
            "libdbus-1-dev",
            "build-essential",
            "git",
            "macchanger",       # required by port-steal tests (MAC address spoofing)
        ]
        self._log("Installing system build dependencies …")
        result = self._run_logged(
            ["apt-get", "install", "-y", "--no-install-recommends"] + pkgs,
            timeout=300,
        )
        if result.returncode != 0:
            self._log(f"WARNING: apt-get install exited {result.returncode} – build may still fail")
            return False
        return True

    def install(self) -> bool:
        """Clone and set up the AirSnitch repository, streaming output to the install log."""
        if self.install_log_file:
            # Start fresh log for this install attempt
            try:
                Path(self.install_log_file).write_text("")
            except Exception:
                pass

        try:
            # Install libnl / openssl / build-essential before attempting compilation
            self._install_system_deps()

            # If dir exists but is incomplete (missing script or compiled binary), wipe and re-clone
            incomplete = self.install_dir.exists() and not self.script.exists()
            if incomplete:
                self._log(f"Incomplete install detected at {self.install_dir} – removing and re-cloning …")
                shutil.rmtree(str(self.install_dir), ignore_errors=True)

            # Fix git "dubious ownership" error when running as a different user
            self._run_logged(
                ["git", "config", "--global", "--add",
                 "safe.directory", str(self.install_dir)],
                timeout=10,
            )

            if not self.install_dir.exists():
                self._log(f"Cloning AirSnitch into {self.install_dir} …")
                result = self._run_logged(
                    ["git", "clone", "--depth", "1", "--recurse-submodules",
                     AIRSNITCH_REPO, str(self.install_dir)],
                    timeout=180,
                )
                if result.returncode != 0:
                    self._log(f"ERROR: git clone failed (exit {result.returncode})")
                    return False
            else:
                self._log("Repository already present – skipping clone.")

            # Run setup.sh if present (initialises git submodules etc.)
            setup = self.install_dir / "setup.sh"
            if setup.exists():
                self._log("Running setup.sh …")
                result = self._run_logged(
                    ["bash", str(setup)],
                    cwd=str(self.install_dir),
                    timeout=900,
                )
                if result.returncode != 0:
                    self._log(f"WARNING: setup.sh exited {result.returncode} – continuing anyway")
            else:
                self._log("No setup.sh found – skipping.")

            # build.sh lives in airsnitch/research/ – compile wpa_supplicant there
            build = self.research_dir / "build.sh"
            if not self.wpa_supplicant_bin.exists():
                if build.exists():
                    self._log("Compiling wpa_supplicant via build.sh (this may take several minutes) …")
                    result = self._run_logged(
                        ["bash", str(build)],
                        cwd=str(self.research_dir),
                        timeout=1800,
                    )
                    if result.returncode != 0:
                        self._log(f"ERROR: build.sh failed (exit {result.returncode})")
                        return False
                else:
                    self._log(f"ERROR: build.sh not found at {build} – cannot compile wpa_supplicant")
                    return False

            if not self.wpa_supplicant_bin.exists():
                self._log("ERROR: wpa_supplicant binary not found after build – compilation may have failed")
                return False

            # pysetup.sh creates the Python venv used by the research scripts
            pysetup = self.research_dir / "pysetup.sh"
            if pysetup.exists():
                self._log("Running pysetup.sh …")
                result = self._run_logged(
                    ["bash", str(pysetup)],
                    cwd=str(self.research_dir),
                    timeout=300,
                )
                if result.returncode != 0:
                    self._log(f"WARNING: pysetup.sh exited {result.returncode} – continuing anyway")

            if not self.script.exists():
                self._log("ERROR: airsnitch.py not found after install")
                return False

            # Make the script executable
            self.script.chmod(self.script.stat().st_mode | 0o111)
            self._log("AirSnitch installed successfully.")
            return True

        except Exception as exc:
            self.logger.error(f"AirSnitch installation failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def write_client_conf(
        self,
        conf_path: Path,
        victim_ssid: str,
        victim_psk: str,
        attacker_ssid: str,
        attacker_psk: str,
        victim_bssid: Optional[str] = None,
    ) -> None:
        """Write a wpa_supplicant-style client.conf for AirSnitch."""
        victim_bssid_line = f"\n    bssid={victim_bssid}" if victim_bssid else ""
        conf = (
            "ctrl_interface=wpaspy_ctrl\n\n"
            "network={\n"
            '    id_str="victim"\n'
            f'    ssid="{victim_ssid}"\n'
            "    key_mgmt=WPA-PSK\n"
            f'    psk="{victim_psk}"{victim_bssid_line}\n'
            "}\n\n"
            "network={\n"
            '    id_str="attacker"\n'
            f'    ssid="{attacker_ssid}"\n'
            "    key_mgmt=WPA-PSK\n"
            f'    psk="{attacker_psk}"\n'
            "}\n"
        )
        conf_path.write_text(conf)

    # ------------------------------------------------------------------
    # Pre-flight checks
    # ------------------------------------------------------------------

    def preflight(self, iface_attacker: str) -> None:
        """Install missing runtime deps and release NM control of the attacker interface."""
        # macchanger is required by the port-steal tests at runtime; install it
        # on-the-fly so tests don't crash even if it was missing at install time.
        if not shutil.which("macchanger"):
            self._log("macchanger not found – installing …")
            self._run_logged(
                ["apt-get", "install", "-y", "--no-install-recommends", "macchanger"],
                timeout=60,
            )

        # Ask NetworkManager to stop managing the attacker interface so it
        # doesn't compete with airsnitch's own wpa_supplicant.
        if shutil.which("nmcli"):
            self._run_logged(
                ["nmcli", "dev", "set", iface_attacker, "managed", "no"],
                timeout=10,
            )
            self._log(
                f"NetworkManager: set {iface_attacker} unmanaged "
                "(will be restored after the scan)"
            )

    # ------------------------------------------------------------------
    # Test runners
    # ------------------------------------------------------------------

    def _run(self, args: list, timeout: int = DEFAULT_TIMEOUT) -> dict:
        """Execute airsnitch.py with the given arguments, streaming output to the run log."""
        cmd = ["python3", str(self.script)] + args
        self._run_log(f"$ {' '.join(cmd)}")
        output_lines: list = []
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.research_dir),  # script references client.conf etc. relatively
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            try:
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    output_lines.append(line)
                    self._run_log(line)
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                self._run_log("ERROR: command timed out")
                return {"returncode": -1, "stdout": "\n".join(output_lines), "stderr": "Timed out"}
            return {
                "returncode": proc.returncode,
                "stdout": "\n".join(output_lines),
                "stderr": "",
            }
        except Exception as exc:
            return {"returncode": -1, "stdout": "", "stderr": str(exc)}

    @staticmethod
    def _is_inconclusive(raw: dict) -> tuple[bool, str]:
        """Return (True, reason) when a test did not produce a conclusive result."""
        stdout_lower = raw.get("stdout", "").lower()
        if "timeout while connecting" in stdout_lower:
            return True, "connection timeout (NetworkManager may be interfering – run: nmcli radio wifi off)"
        if "traceback (most recent call last)" in stdout_lower:
            # Surface the last line of the traceback as the reason
            lines = raw.get("stdout", "").splitlines()
            last = next((l.strip() for l in reversed(lines) if l.strip()), "unknown error")
            return True, f"crashed: {last}"
        if raw.get("returncode", 0) == -1:
            return True, raw.get("stderr") or "command timed out"
        return False, ""

    def test_gtk_shared(
        self, iface_victim: str, iface_attacker: str, same_bss: bool = False
    ) -> dict:
        """Test GTK Abuse – checks whether victim and attacker receive the same group key."""
        bss_flag = "--same-bss" if same_bss else "--other-bss"
        raw = self._run(
            [iface_attacker, "--check-gtk-shared", iface_victim,
             "--no-ssid-check", bss_flag]
        )
        inconclusive, reason = self._is_inconclusive(raw)
        # airsnitch prints both GTK values but never says "gtk is shared".
        # Detect a shared GTK by extracting both values and comparing them.
        victim_m = re.search(r"victim's gtk is \(([^)]+)\)", raw["stdout"], re.IGNORECASE)
        attacker_m = re.search(r"attacker's gtk is \(([^)]+)\)", raw["stdout"], re.IGNORECASE)
        if not inconclusive and victim_m and attacker_m:
            vulnerable = victim_m.group(1) == attacker_m.group(1)
        else:
            vulnerable = False
        return {
            "test": "gtk_shared",
            "vulnerable": vulnerable,
            "inconclusive": inconclusive,
            "inconclusive_reason": reason,
            "same_bss": same_bss,
            **raw,
        }

    def test_gateway_bouncing(
        self, iface_victim: str, iface_attacker: str, same_bss: bool = False
    ) -> dict:
        """Test Gateway Bouncing – checks IP-layer isolation via the gateway."""
        bss_flag = "--same-bss" if same_bss else "--other-bss"
        raw = self._run(
            [iface_attacker, "--c2c-ip", iface_victim,
             "--no-ssid-check", bss_flag]
        )
        inconclusive, reason = self._is_inconclusive(raw)
        vulnerable = (not inconclusive and
                      "client to client traffic at ip layer is allowed" in raw["stdout"].lower())
        return {
            "test": "gateway_bouncing",
            "vulnerable": vulnerable,
            "inconclusive": inconclusive,
            "inconclusive_reason": reason,
            "same_bss": same_bss,
            **raw,
        }

    def test_port_steal_downlink(
        self, iface_victim: str, iface_attacker: str, server: str = "8.8.8.8"
    ) -> dict:
        """Test Downlink Port Stealing across different access points."""
        raw = self._run(
            [iface_attacker, "--c2c-port-steal", iface_victim,
             "--no-ssid-check", "--other-bss", "--server", server]
        )
        inconclusive, reason = self._is_inconclusive(raw)
        vulnerable = (not inconclusive and
                      "downlink port stealing is successful" in raw["stdout"].lower())
        return {
            "test": "port_steal_downlink",
            "vulnerable": vulnerable,
            "inconclusive": inconclusive,
            "inconclusive_reason": reason,
            "server": server,
            **raw,
        }

    def test_port_steal_uplink(
        self, iface_victim: str, iface_attacker: str,
        same_bss: bool = False, server: Optional[str] = None
    ) -> dict:
        """Test Uplink Port Stealing."""
        bss_flag = "--same-bss" if same_bss else "--other-bss"
        args = [iface_attacker, "--c2c-port-steal-uplink", iface_victim,
                "--no-ssid-check", bss_flag]
        if server:
            args += ["--server", server]
        raw = self._run(args)
        inconclusive, reason = self._is_inconclusive(raw)
        vulnerable = (not inconclusive and
                      "uplink port stealing is successful" in raw["stdout"].lower())
        return {
            "test": "port_steal_uplink",
            "vulnerable": vulnerable,
            "inconclusive": inconclusive,
            "inconclusive_reason": reason,
            "same_bss": same_bss,
            "server": server,
            **raw,
        }


# ==============================================================================
# Ragnar action wrapper
# ==============================================================================

class AirSnitch:
    """
    Ragnar action wrapper for AirSnitch Wi-Fi client isolation testing.

    Configuration (read from shared_data.config):
        airsnitch_iface_victim   – wireless interface acting as victim   (default: wlan1)
        airsnitch_iface_attacker – wireless interface acting as attacker (default: wlan2)
        airsnitch_tests          – list of tests to run; options:
                                     "gtk", "gateway", "port_steal_down", "port_steal_up"
                                   (default: all four)
        airsnitch_same_bss       – bool, True to test same BSS scenarios (default: False)
        airsnitch_server         – pingable server IP for port-steal tests (default: "8.8.8.8")
    """

    def __init__(self, shared_data):
        self.shared_data = shared_data
        self.port = None   # Standalone action
        self.b_parent_action = None
        self.logger = logging.getLogger(__name__)

        install_dir = os.path.join(
            getattr(shared_data, "currentdir", "/opt/ragnar"),
            "tools", "airsnitch",
        )
        self.results_dir = Path(
            getattr(shared_data, "logsdir", "/tmp/ragnar_logs"), "airsnitch"
        )
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.install_log_path = self.results_dir / "install.log"
        self.run_log_path = self.results_dir / "run.log"
        self.runner = AirSnitchRunner(install_dir, self.logger, log_file=self.install_log_path)
        self.runner.run_log_file = self.run_log_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cfg(self, key: str, default=None):
        cfg = getattr(self.shared_data, "config", {})
        return cfg.get(key, default)

    def _save_results(self, results: dict) -> Path:
        ts = int(time.time())
        path = self.results_dir / f"airsnitch_{ts}.json"
        path.write_text(json.dumps(results, indent=2, default=str))
        self.logger.info(f"AirSnitch results saved to {path}")
        return path

    # ------------------------------------------------------------------
    # Entry point called by Ragnar orchestrator
    # ------------------------------------------------------------------

    def execute(self, ip=None, port=None, row=None, status_key=None):
        """Run the configured AirSnitch tests and persist results."""
        self.logger.info("AirSnitch: starting Wi-Fi client isolation test")

        # Ensure AirSnitch is available (script + compiled wpa_supplicant)
        if not self.runner.is_installed():
            self.logger.info("AirSnitch not installed – attempting installation …")
            if not self.runner.install():
                self.logger.error("AirSnitch installation failed – skipping")
                return "failed"

        # Extra sanity check: wpa_supplicant binary must exist
        if not self.runner.wpa_supplicant_bin.exists():
            self.logger.error(
                f"AirSnitch requires a compiled wpa_supplicant at "
                f"{self.runner.wpa_supplicant_bin}. "
                f"Run 'bash build.sh' inside {self.runner.install_dir} to build it."
            )
            return "failed"

        iface_victim   = self._cfg("airsnitch_iface_victim",   "wlan1")
        iface_attacker = self._cfg("airsnitch_iface_attacker", "wlan2")
        tests          = self._cfg("airsnitch_tests",          ["gtk", "gateway", "port_steal_down", "port_steal_up"])
        same_bss       = self._cfg("airsnitch_same_bss",       False)
        server         = self._cfg("airsnitch_server",         "8.8.8.8")

        victim_ssid    = self._cfg("airsnitch_victim_ssid")
        victim_psk     = self._cfg("airsnitch_victim_psk")
        attacker_ssid  = self._cfg("airsnitch_attacker_ssid")
        attacker_psk   = self._cfg("airsnitch_attacker_psk")

        # Pre-flight: install missing runtime tools and release NM's grip
        self.runner.preflight(iface_attacker)

        # Write client.conf if credentials are provided
        if victim_ssid and victim_psk and attacker_ssid and attacker_psk:
            conf_path = self.runner.research_dir / "client.conf"
            self.logger.info(f"AirSnitch: writing client.conf to {conf_path}")
            self.runner.write_client_conf(
                conf_path,
                victim_ssid=victim_ssid,
                victim_psk=victim_psk,
                attacker_ssid=attacker_ssid,
                attacker_psk=attacker_psk,
            )
        else:
            self.logger.info("AirSnitch: no SSID/PSK configured – using existing client.conf")

        self.logger.info(
            f"AirSnitch: victim={iface_victim} attacker={iface_attacker} "
            f"same_bss={same_bss} tests={tests}"
        )

        # Clear the run log for this fresh run
        try:
            self.run_log_path.write_text("")
        except Exception:
            pass

        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "iface_victim": iface_victim,
            "iface_attacker": iface_attacker,
            "tests": {},
        }

        self._running = True
        try:
            if "gtk" in tests:
                self.logger.info("AirSnitch: running GTK shared-key test …")
                results["tests"]["gtk_shared"] = self.runner.test_gtk_shared(
                    iface_victim, iface_attacker, same_bss=same_bss
                )

            if "gateway" in tests:
                self.logger.info("AirSnitch: running gateway bouncing test …")
                results["tests"]["gateway_bouncing"] = self.runner.test_gateway_bouncing(
                    iface_victim, iface_attacker, same_bss=same_bss
                )

            if "port_steal_down" in tests:
                self.logger.info("AirSnitch: running downlink port-steal test …")
                results["tests"]["port_steal_downlink"] = self.runner.test_port_steal_downlink(
                    iface_victim, iface_attacker, server=server
                )

            if "port_steal_up" in tests:
                self.logger.info("AirSnitch: running uplink port-steal test …")
                results["tests"]["port_steal_uplink"] = self.runner.test_port_steal_uplink(
                    iface_victim, iface_attacker, same_bss=same_bss, server=server
                )

            # Summarise findings
            vulnerable_tests = [
                name for name, data in results["tests"].items()
                if isinstance(data, dict) and data.get("vulnerable")
            ]
            inconclusive_tests = [
                name for name, data in results["tests"].items()
                if isinstance(data, dict) and data.get("inconclusive")
            ]
            conclusive_tests = len(results["tests"]) - len(inconclusive_tests)
            results["summary"] = {
                "total_tests": len(results["tests"]),
                "vulnerable_count": len(vulnerable_tests),
                "vulnerable_tests": vulnerable_tests,
                "inconclusive_tests": inconclusive_tests,
                # only declare network isolated when ALL tests ran AND none were vulnerable
                "network_isolated": len(vulnerable_tests) == 0 and len(inconclusive_tests) == 0,
            }

            self._save_results(results)

            if vulnerable_tests:
                self.logger.warning(
                    f"AirSnitch: network FAILS client isolation – "
                    f"vulnerable to: {', '.join(vulnerable_tests)}"
                )
            if inconclusive_tests:
                reasons = {
                    name: results["tests"][name].get("inconclusive_reason", "unknown")
                    for name in inconclusive_tests
                }
                reason_str = "; ".join(f"{n}: {r}" for n, r in reasons.items())
                self.logger.warning(
                    f"AirSnitch: {len(inconclusive_tests)} test(s) inconclusive – {reason_str}"
                )
                if all("timeout while connecting" in r for r in reasons.values()):
                    self.logger.warning(
                        "AirSnitch: all timeouts are likely caused by NetworkManager competing "
                        "for the wireless interface. Run: nmcli radio wifi off"
                    )
            if not vulnerable_tests and not inconclusive_tests:
                self.logger.info("AirSnitch: network passes all client isolation tests")
            elif not vulnerable_tests and conclusive_tests == 0:
                self.logger.warning(
                    "AirSnitch: no conclusive results – all tests failed to complete"
                )

            return "success"

        except Exception as exc:
            self.logger.error(f"AirSnitch execution error: {exc}", exc_info=True)
            results["error"] = str(exc)
            self._save_results(results)
            return "failed"

        finally:
            # Restore NetworkManager management of the attacker interface
            if shutil.which("nmcli"):
                subprocess.run(
                    ["nmcli", "dev", "set", iface_attacker, "managed", "yes"],
                    timeout=10, capture_output=True,
                )
            self._running = False

    def get_latest_results(self) -> Optional[dict]:
        """Return the most recent saved results, or None if none exist."""
        files = sorted(self.results_dir.glob("airsnitch_*.json"), reverse=True)
        if not files:
            return None
        try:
            return json.loads(files[0].read_text())
        except Exception:
            return None

    def get_install_log(self) -> str:
        """Return the current contents of the install log (empty string if none)."""
        try:
            return self.install_log_path.read_text()
        except Exception:
            return ""

    def get_run_log(self) -> str:
        """Return the current contents of the test run log (empty string if none)."""
        return self.runner.get_run_log()

    def is_installing(self) -> bool:
        """True while an install thread is running."""
        return getattr(self, "_installing", False)

    def is_running(self) -> bool:
        """True while a test run thread is active."""
        return getattr(self, "_running", False)
