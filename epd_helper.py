# epd_helper.py

import importlib
import logging
import time

logger = logging.getLogger(__name__)

# Known EPD types to try during auto-detection (most common first)
KNOWN_EPD_TYPES = [
    "epd2in13_V4",
    "epd2in13_V3",
    "epd2in13_V2",
    "epd2in7",
    "epd2in13",
    "epd2in9_V2",
    "epd3in7",
]

class EPDHelper:
    def __init__(self, epd_type):
        self.epd_type = epd_type
        self.epd = self._load_epd_module()

    def _load_epd_module(self):
        try:
            epd_module_name = f'resources.waveshare_epd.{self.epd_type}'
            epd_module = importlib.import_module(epd_module_name)
            return epd_module.EPD()
        except ImportError as e:
            logger.error(f"EPD module {self.epd_type} not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading EPD module {self.epd_type}: {e}")
            raise

    def init_full_update(self):
        try:
            if hasattr(self.epd, 'FULL_UPDATE'):
                self.epd.init(self.epd.FULL_UPDATE)
            elif hasattr(self.epd, 'lut_full_update'):
                self.epd.init(self.epd.lut_full_update)
            else:
                self.epd.init()
            logger.info("EPD full update initialization complete.")
        except Exception as e:
            logger.error(f"Error initializing EPD for full update: {e}")
            raise

    def init_partial_update(self):
        try:
            if hasattr(self.epd, 'PART_UPDATE'):
                self.epd.init(self.epd.PART_UPDATE)
            elif hasattr(self.epd, 'lut_partial_update'):
                self.epd.init(self.epd.lut_partial_update)
            else:
                self.epd.init()
            logger.info("EPD partial update initialization complete.")
        except Exception as e:
            logger.error(f"Error initializing EPD for partial update: {e}")
            raise

    def display_partial(self, image):
        try:
            if hasattr(self.epd, 'displayPartial'):
                self.epd.displayPartial(self.epd.getbuffer(image))
            elif hasattr(self.epd, 'display_Partial'):
                self.epd.display_Partial(self.epd.getbuffer(image))
            else:
                self.epd.display(self.epd.getbuffer(image))
            logger.info("Partial display update complete.")
        except Exception as e:
            logger.error(f"Error during partial display update: {e}")
            raise

    def clear(self):
        try:
            self.epd.Clear()
            logger.info("EPD cleared.")
        except Exception as e:
            logger.error(f"Error clearing EPD: {e}")
            raise

    def display_full(self, image):
        """Display image on EPD using full update."""
        try:
            self.epd.display(self.epd.getbuffer(image))
            logger.info("Full display update complete.")
        except Exception as e:
            logger.error(f"Error during full display update: {e}")
            raise

    def sleep(self):
        """Put EPD to sleep mode."""
        try:
            self.epd.sleep()
            logger.info("EPD sleep mode activated.")
        except Exception as e:
            logger.error(f"Error putting EPD to sleep: {e}")
            raise

    @staticmethod
    def auto_detect(known_types=None):
        """Try each known EPD driver and return the first that initializes successfully.

        Returns:
            tuple: (epd_type_string, width, height) on success, or None if no display detected.
        """
        if known_types is None:
            known_types = KNOWN_EPD_TYPES

        for epd_type in known_types:
            try:
                logger.info(f"Auto-detect: trying {epd_type}...")
                helper = EPDHelper(epd_type)
                helper.epd.init()
                w, h = helper.epd.width, helper.epd.height
                try:
                    helper.epd.sleep()
                except Exception:
                    pass
                time.sleep(0.3)
                logger.info(f"Auto-detect: found {epd_type} ({w}x{h})")
                return (epd_type, w, h)
            except Exception as e:
                logger.debug(f"Auto-detect: {epd_type} failed: {e}")
                try:
                    helper.epd.sleep()
                except Exception:
                    pass
                time.sleep(0.3)
        logger.warning("Auto-detect: no e-paper display detected")
        return None