#pager_display.py
# Description:
# Pager LCD display module for Ragnar - renders the Viking-themed status display
# on the WiFi Pineapple Pager's 222x480 RGB565 LCD via libpagerctl.so.
# Adapted from pineapple_pager_bjorn's display.py for Ragnar naming conventions.

import threading
import time
import os
import sys
import signal
import logging
import random
import glob
import subprocess
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pagerctl import Pager
from init_shared import shared_data
from comment import Commentaireia
from logger import Logger

logger = Logger(name="pager_display.py", level=logging.INFO)

PAYLOAD_DIR = os.path.dirname(os.path.abspath(__file__))


def discover_launchers():
    """Scan PAYLOAD_DIR for launch_*.sh scripts with valid # Requires: paths.
    Returns list of (title, path) tuples."""
    launchers = []
    pattern = os.path.join(PAYLOAD_DIR, 'launch_*.sh')
    matches = sorted(glob.glob(pattern))
    for path in matches:
        basename = os.path.basename(path)
        if basename == 'launch_ragnar.sh':
            continue
        title = None
        requires = None
        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('# Title:'):
                        title = line[len('# Title:'):].strip()
                    elif line.startswith('# Requires:'):
                        requires = line[len('# Requires:'):].strip()
                    if title and requires:
                        break
        except Exception as e:
            logger.error(f"discover_launchers: error reading {path}: {e}")
            continue
        if not title:
            continue
        if requires and not os.path.isdir(requires):
            continue
        launchers.append((title, path))
    return launchers


class PagerDisplay:
    """Pager LCD display for Ragnar - matches original layout."""

    def __init__(self, shared_data):
        self.shared_data = shared_data
        self.config = self.shared_data.config
        self.shared_data.ragnarstatustext2 = "Awakening..."
        self.commentaire_ia = Commentaireia()
        self.semaphore = threading.Semaphore(10)

        # Initialize pagerctl
        try:
            logger.info("Initializing pagerctl display...")
            self.pager = Pager()
            self.pager.init()
            self.pager.set_rotation(0)  # Portrait 222x480

            self.width = self.pager.width    # 222
            self.height = self.pager.height  # 480
            logger.info(f"Pager display initialized: {self.width}x{self.height}")

            self.shared_data.width = self.width
            self.shared_data.height = self.height

        except Exception as e:
            logger.error(f"Error initializing pagerctl: {e}")
            raise

        # Colors
        self.BLACK = self.pager.BLACK
        self.WHITE = self.pager.WHITE
        self.GRAY = self.pager.rgb(128, 128, 128)

        # Fonts
        self.font_arial = self.shared_data.font_arial_path
        self.font_viking = self.shared_data.font_viking_path

        # Scale factors (original 122x250 -> pager 222x480)
        self.sx = self.width / 122.0   # ~1.82
        self.sy = self.height / 250.0  # ~1.92

        # Current animation frame
        self.main_image_path = None
        self.manual_mode_txt = "M" if self.shared_data.manual_mode else "A"
        self.last_led_status = None
        self.dialog_showing = False

        # Brightness/dim settings
        self.screen_brightness = getattr(self.shared_data, 'screen_brightness', 80)
        self.screen_dim_brightness = getattr(self.shared_data, 'screen_dim_brightness', 20)
        self.screen_dim_timeout = getattr(self.shared_data, 'screen_dim_timeout', 60)
        self.last_activity_time = time.time()
        self.is_dimmed = False

        # Set initial brightness
        try:
            self.pager.set_brightness(self.screen_brightness)
            logger.info(f"Screen brightness set to {self.screen_brightness}%")
        except Exception as e:
            logger.debug(f"Could not set brightness: {e}")

        self.start_threads()
        logger.info("PagerDisplay initialization complete.")

    def start_threads(self):
        threading.Thread(target=self.update_main_image, daemon=True).start()
        threading.Thread(target=self.schedule_update_shared_data, daemon=True).start()
        threading.Thread(target=self.schedule_update_vuln_count, daemon=True).start()
        threading.Thread(target=self.handle_input_loop, daemon=True).start()

    def update_main_image(self):
        while not self.shared_data.display_should_exit:
            try:
                self.shared_data.update_image_randomizer()
                if self.shared_data.current_image_path:
                    self.main_image_path = self.shared_data.current_image_path
                delay = random.uniform(
                    self.shared_data.image_display_delaymin,
                    self.shared_data.image_display_delaymax
                )
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in update_main_image: {e}")
                time.sleep(1)

    def schedule_update_shared_data(self):
        while not self.shared_data.display_should_exit:
            self.update_shared_data()
            time.sleep(25)

    def schedule_update_vuln_count(self):
        while not self.shared_data.display_should_exit:
            self.update_vuln_count()
            time.sleep(300)

    def wake_screen(self):
        if self.is_dimmed:
            try:
                self.pager.set_brightness(self.screen_brightness)
                self.is_dimmed = False
            except Exception:
                pass
        self.last_activity_time = time.time()

    def dim_screen(self):
        if not self.is_dimmed:
            try:
                self.pager.set_brightness(self.screen_dim_brightness)
                self.is_dimmed = True
            except Exception:
                pass

    def check_dim_timeout(self):
        if self.screen_dim_timeout > 0 and not self.is_dimmed:
            if time.time() - self.last_activity_time > self.screen_dim_timeout:
                self.dim_screen()

    def handle_input_loop(self):
        """Handle button input - Red button shows pause menu."""
        logger.info("Input handler: Monitoring for button presses")
        while not self.shared_data.display_should_exit:
            try:
                button = self.pager.wait_button()
                self.wake_screen()

                if button & self.pager.BTN_B:
                    logger.info("Red button pressed - showing pause menu")
                    action = self.show_exit_confirmation()
                    if action is None:
                        continue
                    logger.info(f"Menu action: exit code {action}")
                    self.shared_data.should_exit = True
                    self.shared_data.display_should_exit = True
                    self.shared_data.orchestrator_should_exit = True
                    if action == 42:
                        data_dir = os.path.join(PAYLOAD_DIR, 'data')
                        os.makedirs(data_dir, exist_ok=True)
                        next_payload_path = os.path.join(data_dir, '.next_payload')
                        with open(next_payload_path, 'w') as f:
                            f.write(self._handoff_launcher_path)
                    self.cleanup()
                    os._exit(action)
            except Exception as e:
                logger.error(f"Error in input handler: {e}")
                time.sleep(1.0)

    def show_exit_confirmation(self):
        """Show pause menu. Returns: None=back, 99=main menu, 42=handoff, 0=exit."""
        self.dialog_showing = True
        time.sleep(0.2)

        current_brightness = self.pager.get_brightness()
        if current_brightness < 0:
            current_brightness = self.screen_brightness

        green_color = self.pager.rgb(0, 150, 0)
        yellow_color = self.pager.rgb(180, 150, 0)
        blue_color = self.pager.rgb(50, 100, 220)
        red_color = self.pager.rgb(200, 0, 0)

        options = [
            ("BACK", green_color, None),
            ("Main Menu", yellow_color, 99),
        ]

        launchers = discover_launchers()
        for title, path in launchers:
            options.append((f"> {title}", blue_color, (42, path)))

        options.append(("Exit Ragnar", red_color, 0))

        num_options = len(options)
        selected = 0

        def draw_menu():
            self.pager.fill_rect(0, 0, self.width, self.height, self.WHITE)
            box_y = int(self.height * 0.10)
            box_h = int(self.height * 0.80)
            self.pager.fill_rect(10, box_y, self.width - 20, box_h, self.WHITE)
            self.pager.rect(10, box_y, self.width - 20, box_h, self.BLACK)
            self.pager.rect(12, box_y + 2, self.width - 24, box_h - 4, self.BLACK)

            title_y = box_y + 15
            self.pager.draw_ttf_centered(title_y, "MENU", self.BLACK, self.font_viking, int(12 * self.sy))

            bright_y = box_y + int(30 * self.sy)
            self.pager.draw_ttf_centered(bright_y, "BRIGHTNESS", self.BLACK, self.font_arial, int(9 * self.sy))

            bar_y = bright_y + int(22 * self.sy)
            bar_x = 30
            bar_w = self.width - 60
            bar_h = int(12 * self.sy)
            self.pager.fill_rect(bar_x, bar_y, bar_w, bar_h, self.GRAY)
            fill_w = int(bar_w * current_brightness / 100)
            self.pager.fill_rect(bar_x, bar_y, fill_w, bar_h, self.BLACK)
            self.pager.rect(bar_x, bar_y, bar_w, bar_h, self.BLACK)

            pct_y = bar_y + bar_h + 5
            self.pager.draw_ttf_centered(pct_y, f"{current_brightness}%", self.BLACK, self.font_arial, int(10 * self.sy))

            btn_w = 120
            btn_h = 28
            btn_x = (self.width - btn_w) // 2
            btn_gap = 8
            font_size = int(8 * self.sy)
            first_btn_y = pct_y + int(18 * self.sy)

            for i, (label, color, _action) in enumerate(options):
                btn_y = first_btn_y + i * (btn_h + btn_gap)
                if i == selected:
                    self.pager.fill_rect(btn_x - 4, btn_y - 4, btn_w + 8, btn_h + 8, self.BLACK)
                self.pager.fill_rect(btn_x, btn_y, btn_w, btn_h, color)
                text_w = self.pager.ttf_width(label, self.font_arial, font_size)
                text_x = btn_x + (btn_w - text_w) // 2
                text_y = btn_y + (btn_h - font_size) // 2
                self.pager.draw_ttf(text_x, text_y, label, self.WHITE, self.font_arial, font_size)

            self.pager.flip()

        draw_menu()

        while True:
            button = self.pager.wait_button()
            if button & self.pager.BTN_DOWN:
                current_brightness = max(20, current_brightness - 10)
                self.pager.set_brightness(current_brightness)
                self.screen_brightness = current_brightness
                draw_menu()
            elif button & self.pager.BTN_UP:
                current_brightness = min(100, current_brightness + 10)
                self.pager.set_brightness(current_brightness)
                self.screen_brightness = current_brightness
                draw_menu()
            elif button & self.pager.BTN_LEFT:
                selected = (selected - 1) % num_options
                draw_menu()
            elif button & self.pager.BTN_RIGHT:
                selected = (selected + 1) % num_options
                draw_menu()
            elif button & self.pager.BTN_A:
                self.dialog_showing = False
                action = options[selected][2]
                if action is None:
                    return None
                elif isinstance(action, tuple):
                    self._handoff_launcher_path = action[1]
                    return 42
                else:
                    return action
            elif button & self.pager.BTN_B:
                self.dialog_showing = False
                return None

    def update_vuln_count(self):
        with self.semaphore:
            try:
                if not os.path.exists(self.shared_data.vuln_summary_file):
                    with open(self.shared_data.vuln_summary_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["IP", "Hostname", "MAC Address", "Port", "Vulnerabilities"])
                    self.shared_data.vulnnbr = 0
                else:
                    alive_macs = set()
                    if os.path.exists(self.shared_data.netkbfile):
                        with open(self.shared_data.netkbfile, 'r') as file:
                            reader = csv.DictReader(file)
                            for row in reader:
                                if row.get("Alive") == "1" and row.get("MAC Address") != "STANDALONE":
                                    alive_macs.add(row.get("MAC Address"))

                    with open(self.shared_data.vuln_summary_file, 'r') as file:
                        reader = csv.DictReader(file)
                        all_vulnerabilities = set()
                        for row in reader:
                            mac_address = row.get("MAC Address", "")
                            if mac_address in alive_macs and mac_address != "STANDALONE":
                                vulnerabilities = row.get("Vulnerabilities", "")
                                if vulnerabilities and isinstance(vulnerabilities, str):
                                    all_vulnerabilities.update(vulnerabilities.split("; "))
                        self.shared_data.vulnnbr = len(all_vulnerabilities)
            except Exception as e:
                logger.error(f"Error in update_vuln_count: {e}")

    def update_shared_data(self):
        with self.semaphore:
            try:
                if os.path.exists(self.shared_data.livestatusfile):
                    with open(self.shared_data.livestatusfile, 'r') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            self.shared_data.portnbr = int(row.get('Total Open Ports', 0) or 0)
                            self.shared_data.targetnbr = int(row.get('Alive Hosts Count', 0) or 0)
                            self.shared_data.networkkbnbr = int(row.get('All Known Hosts Count', 0) or 0)
                            self.shared_data.vulnnbr = int(row.get('Vulnerabilities Count', 0) or 0)
                            break

                crackedpw_files = glob.glob(f"{self.shared_data.crackedpwddir}/*.csv")
                total_passwords = 0
                for filepath in crackedpw_files:
                    try:
                        with open(filepath, 'r') as f:
                            reader = csv.reader(f)
                            next(reader, None)
                            total_passwords += sum(1 for _ in reader)
                    except Exception:
                        pass
                self.shared_data.crednbr = total_passwords

                total_data = sum([len(files) for r, d, files in os.walk(self.shared_data.datastolendir)])
                self.shared_data.datanbr = total_data

                total_zombies = sum([len(files) for r, d, files in os.walk(self.shared_data.zombiesdir)])
                self.shared_data.zombiesnbr = total_zombies

                self.shared_data.update_stats()
                self.shared_data.manual_mode = self.is_manual_mode()
                self.manual_mode_txt = "M" if self.shared_data.manual_mode else "A"
                self.shared_data.wifi_connected = self.is_wifi_connected()

            except FileNotFoundError as e:
                logger.debug(f"Data file not ready: {e}")
            except Exception as e:
                logger.error(f"Error updating shared data: {e}")

    def display_comment(self, status):
        comment = self.commentaire_ia.get_commentaire(status)
        if comment:
            self.shared_data.ragnarsays = comment
            self.shared_data.ragnarstatustext = self.shared_data.ragnarorch_status

    def is_wifi_connected(self):
        try:
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, timeout=5)
            return bool(result.stdout.strip())
        except Exception:
            return False

    def is_manual_mode(self):
        return self.shared_data.manual_mode

    def update_leds(self, status):
        if status == self.last_led_status:
            return
        self.last_led_status = status
        try:
            if status == "IDLE":
                self.pager.led_dpad("up", 0x000033)
                self.pager.led_dpad("down", 0x000033)
                self.pager.led_dpad("left", 0x000033)
                self.pager.led_dpad("right", 0x000033)
            elif "Scanner" in status or "Scan" in status:
                self.pager.led_dpad("up", 0x00FFFF)
                self.pager.led_dpad("down", 0x003333)
                self.pager.led_dpad("left", 0x003333)
                self.pager.led_dpad("right", 0x00FFFF)
            elif "Bruteforce" in status:
                self.pager.led_dpad("up", 0xFF0000)
                self.pager.led_dpad("down", 0xFF0000)
                self.pager.led_dpad("left", 0x330000)
                self.pager.led_dpad("right", 0x330000)
            elif "Steal" in status:
                self.pager.led_dpad("up", 0xFFFF00)
                self.pager.led_dpad("down", 0x333300)
                self.pager.led_dpad("left", 0xFFFF00)
                self.pager.led_dpad("right", 0x333300)
            else:
                self.pager.led_dpad("up", 0x00FF00)
                self.pager.led_dpad("down", 0x003300)
                self.pager.led_dpad("left", 0x003300)
                self.pager.led_dpad("right", 0x00FF00)
        except Exception as e:
            logger.debug(f"LED update error: {e}")

    def sanitize_text(self, text):
        if not text:
            return text
        replacements = {
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': '-', '\u2026': '...',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def draw_icon(self, x, y, icon_name):
        icon_path = self.shared_data.static_images.get(icon_name)
        if icon_path and os.path.exists(icon_path):
            try:
                self.pager.draw_image_file(x, y, icon_path)
                return True
            except Exception:
                pass
        return False

    def draw_icon_scaled(self, x, y, w, h, icon_name):
        icon_path = self.shared_data.static_images.get(icon_name)
        if icon_path and os.path.exists(icon_path):
            try:
                self.pager.draw_image_file_scaled(x, y, w, h, icon_path)
                return True
            except Exception:
                pass
        return False

    def draw_header(self):
        y = 0
        h = int(20 * self.sy)
        self.pager.fill_rect(0, y, self.width, h, self.WHITE)
        self.pager.hline(0, h - 1, self.width, self.BLACK)

        left_icon_size = int(10 * self.sy)
        right_icon_size = int(10 * self.sy)

        x = 2
        icon_y = (h - left_icon_size) // 2
        self.draw_icon_scaled(x, icon_y, left_icon_size, left_icon_size, 'wifi')
        x += left_icon_size + 6
        self.draw_icon_scaled(x, icon_y, left_icon_size, left_icon_size, 'bluetooth')

        title_font_size = int(14 * self.sy)
        self.pager.draw_ttf_centered(int(5 * self.sy), "RAGNAR", self.BLACK, self.font_viking, title_font_size)

        icon_y_r = (h - right_icon_size) // 2
        x = self.width - right_icon_size - 2
        self.draw_icon_scaled(x, icon_y_r, right_icon_size, right_icon_size, 'connected')
        x -= right_icon_size + 6
        self.draw_icon_scaled(x, icon_y_r, right_icon_size, right_icon_size, 'usb')

    def draw_stats_grid(self):
        y_start = int(22 * self.sy)
        h = int(40 * self.sy)
        self.pager.fill_rect(0, y_start, self.width, h, self.WHITE)
        self.pager.rect(0, y_start, self.width, h, self.BLACK)

        col_w = self.width // 3
        row_h = h // 2

        stats = [
            [('target', self.shared_data.targetnbr),
             ('port', self.shared_data.portnbr),
             ('vuln', self.shared_data.vulnnbr)],
            [('cred', self.shared_data.crednbr),
             ('zombie', self.shared_data.zombiesnbr),
             ('data', self.shared_data.datanbr)],
        ]

        icon_size = int(16 * self.sy)
        font_size = int(12 * self.sy)

        for row_idx, row in enumerate(stats):
            for col_idx, (icon_name, value) in enumerate(row):
                cx = col_idx * col_w
                cy = y_start + row_idx * row_h
                icon_x = cx + 4
                icon_y = cy + (row_h - icon_size) // 2
                self.draw_icon_scaled(icon_x, icon_y, icon_size, icon_size, icon_name)
                text_x = icon_x + icon_size + 4
                text_y = cy + (row_h - font_size) // 2
                self.pager.draw_ttf(text_x, text_y, str(value), self.BLACK, self.font_arial, font_size)

        for i in range(1, 3):
            self.pager.vline(i * col_w, y_start, h, self.BLACK)
        self.pager.hline(0, y_start + row_h, self.width, self.BLACK)

    def draw_status_area(self):
        y_start = int(62 * self.sy)
        h = int(28 * self.sy)
        self.pager.fill_rect(0, y_start, self.width, h, self.WHITE)
        self.pager.rect(0, y_start, self.width, h, self.BLACK)

        icon_size = int(24 * self.sy)
        icon_x = 6
        icon_y = y_start + (h - icon_size) // 2

        if self.shared_data.ragnarstatusimage_path and os.path.exists(self.shared_data.ragnarstatusimage_path):
            try:
                self.pager.draw_image_file_scaled(icon_x, icon_y, icon_size, icon_size,
                                                   self.shared_data.ragnarstatusimage_path)
            except Exception:
                pass

        text_x = icon_x + icon_size + 8
        main_font = int(12 * self.sy)
        sub_font = int(10 * self.sy)

        status_text = self.shared_data.ragnarstatustext[:16]
        self.pager.draw_ttf(text_x, y_start + 4, status_text, self.BLACK, self.font_arial, main_font)

        status_text2 = self.shared_data.ragnarstatustext2[:20]
        self.pager.draw_ttf(text_x, y_start + 4 + main_font + 2, status_text2, self.GRAY, self.font_arial, sub_font)

    def draw_dialogue_zone(self):
        y_start = int(90 * self.sy)
        h = int(70 * self.sy)
        self.pager.fill_rect(0, y_start, self.width, h, self.WHITE)
        self.pager.rect(0, y_start, self.width, h, self.BLACK)

        font_size = int(12 * self.sy)
        line_height = int(14 * self.sy)
        max_chars = 21

        text_y = y_start + 8
        if hasattr(self.shared_data, 'ragnarsays') and self.shared_data.ragnarsays:
            clean_text = self.sanitize_text(self.shared_data.ragnarsays)
            lines = self.shared_data.wrap_text(clean_text, max_chars=max_chars)
            for i, line in enumerate(lines[:4]):
                self.pager.draw_ttf(8, text_y + i * line_height, line, self.BLACK, self.font_arial, font_size)

    def draw_frise(self):
        y = int(155 * self.sy)
        frise_path = self.shared_data.static_images.get('frise')
        if frise_path and os.path.exists(frise_path):
            try:
                frise_h = int(12 * self.sy)
                self.pager.draw_image_file_scaled(0, y, self.width, frise_h, frise_path)
            except Exception:
                self.pager.hline(0, y + 5, self.width, self.BLACK)
                self.pager.hline(0, y + 7, self.width, self.BLACK)

    def draw_character_and_corner_stats(self):
        char_top = int(175 * self.sy)
        char_bottom = self.height - 25

        char_w = int(70 * self.sx)
        char_h = int(80 * self.sy)
        char_x = (self.width - char_w) // 2
        char_y = char_top + (char_bottom - char_top - char_h) // 2

        if self.main_image_path and os.path.exists(self.main_image_path):
            try:
                self.pager.draw_image_file_scaled(char_x, char_y, char_w, char_h, self.main_image_path)
            except Exception:
                self.pager.draw_ttf(char_x + 20, char_y + 30, "?", self.BLACK, self.font_viking, 36)

        icon_size = int(18 * self.sy)
        num_font = int(16 * self.sy)

        # TOP-LEFT: Coins
        x = 4
        y = char_y + 15
        self.draw_icon_scaled(x, y, icon_size, icon_size, 'gold')
        self.pager.draw_ttf(x, y + icon_size + 2, str(self.shared_data.coinnbr), self.BLACK, self.font_arial, num_font)

        # BOTTOM-LEFT: Level
        x = 4
        y = char_y + char_h - icon_size - num_font - 4
        self.draw_icon_scaled(x, y, icon_size, icon_size, 'level')
        self.pager.draw_ttf(x, y + icon_size + 2, str(self.shared_data.levelnbr), self.BLACK, self.font_arial, num_font)

        # TOP-RIGHT: Network KB
        x = self.width - icon_size - 4
        y = char_y + 15
        self.draw_icon_scaled(x, y, icon_size, icon_size, 'networkkb')
        self.pager.draw_ttf(x, y + icon_size + 2, str(self.shared_data.networkkbnbr), self.BLACK, self.font_arial, num_font)

        # BOTTOM-RIGHT: Attacks
        x = self.width - icon_size - 4
        y = char_y + char_h - icon_size - num_font - 4
        self.draw_icon_scaled(x, y, icon_size, icon_size, 'attacks')
        self.pager.draw_ttf(x, y + icon_size + 2, str(self.shared_data.attacksnbr), self.BLACK, self.font_arial, num_font)

    def render_frame(self):
        if self.dialog_showing:
            return
        self.pager.clear(self.WHITE)
        self.draw_header()
        self.draw_stats_grid()
        self.draw_status_area()
        self.draw_dialogue_zone()
        self.draw_frise()
        self.draw_character_and_corner_stats()
        if not self.dialog_showing:
            self.pager.flip()

    def run(self):
        logger.info("Starting pager display main loop...")
        while not self.shared_data.display_should_exit:
            try:
                if self.dialog_showing:
                    time.sleep(0.1)
                    continue
                self.check_dim_timeout()
                self.display_comment(self.shared_data.ragnarorch_status)
                self.shared_data.update_ragnarstatus()
                self.update_leds(self.shared_data.ragnarorch_status)
                self.render_frame()
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in display loop: {e}")
                time.sleep(0.1)
        logger.info("Pager display loop exiting...")
        self.cleanup()

    def cleanup(self):
        try:
            logger.info("Cleaning up pager display...")
            self.pager.led_all_off()
            self.pager.clear(self.BLACK)
            self.pager.flip()
            self.pager.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def handle_exit_pager_display(signum, frame, display_instance=None, exit_process=True):
    logger.info("Exit signal received...")
    shared_data.display_should_exit = True
    shared_data.should_exit = True
    if display_instance:
        display_instance.cleanup()
    if exit_process:
        sys.exit(0)


if __name__ == "__main__":
    display_instance = None
    try:
        logger.info("Starting Ragnar pager display...")
        display_instance = PagerDisplay(shared_data)
        signal.signal(signal.SIGINT, lambda s, f: handle_exit_pager_display(s, f, display_instance))
        signal.signal(signal.SIGTERM, lambda s, f: handle_exit_pager_display(s, f, display_instance))
        display_instance.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if display_instance:
            display_instance.cleanup()
        sys.exit(1)
