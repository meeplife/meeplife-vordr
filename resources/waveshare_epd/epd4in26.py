# *****************************************************************************
# * | File        :	  epd4in26.py
# * | Author      :   Waveshare team
# * | Function    :   Electronic paper driver
# * | Info        :
# *----------------
# * | This version:   V1.0
# * | Date        :   2023-06-25
# # | Info        :   python demo
# -----------------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
from . import epdconfig

# Display resolution
EPD_WIDTH       = 800
EPD_HEIGHT      = 480

logger = logging.getLogger(__name__)

class EPD:
    def __init__(self):
        self.is_initialized = False  # Track if the display has been initialized (Ragnar compatibility)
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin = epdconfig.DC_PIN
        self.busy_pin = epdconfig.BUSY_PIN
        self.cs_pin = epdconfig.CS_PIN
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

    def reset(self):
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(2)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)

    def send_command(self, command):
        epdconfig.digital_write(self.dc_pin, 0)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([command])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data2(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte2(data)
        epdconfig.digital_write(self.cs_pin, 1)

    def ReadBusy(self):
        logger.debug("e-Paper busy")
        while(epdconfig.digital_read(self.busy_pin) == 0):      # 0: idle, 1: busy
            epdconfig.delay_ms(10)
        logger.debug("e-Paper busy release")

    def TurnOnDisplay(self):
        self.send_command(0x22)
        self.send_data(0xF7)
        self.send_command(0x20)
        self.ReadBusy()

    def TurnOnDisplayPart(self):
        self.send_command(0x22)
        self.send_data(0xFF)
        self.send_command(0x20)
        self.ReadBusy()

    def init(self):
        if not self.is_initialized:
            if (epdconfig.module_init() != 0):
                return -1
            self.is_initialized = True

        self.reset()

        self.ReadBusy()
        self.send_command(0x12)  # SWRESET
        self.ReadBusy()

        self.send_command(0x18)  # Read built-in temperature sensor
        self.send_data(0x80)

        self.send_command(0x0C)  # Booster soft start control
        self.send_data(0xAE)
        self.send_data(0xC7)
        self.send_data(0xC3)
        self.send_data(0xC0)
        self.send_data(0x80)

        self.send_command(0x01)  # Driver output control
        self.send_data(0xDF)
        self.send_data(0x01)
        self.send_data(0x00)

        self.send_command(0x11)  # Data entry mode
        self.send_data(0x03)

        self.send_command(0x44)  # Set RAM X start/end position
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x63)
        self.send_data(0x00)

        self.send_command(0x45)  # Set RAM Y start/end position
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0xDF)
        self.send_data(0x01)

        self.send_command(0x3C)  # Border waveform
        self.send_data(0x01)

        self.send_command(0x2C)  # VCOM
        self.send_data(0x36)

        self.send_command(0x3F)
        self.send_data(0x22)

        self.send_command(0x03)
        self.send_data(0x17)

        self.send_command(0x04)
        self.send_data(0x41)
        self.send_data(0xAC)
        self.send_data(0x32)

        self.send_command(0x37)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x4E)  # Set RAM X address counter
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x4F)  # Set RAM Y address counter
        self.send_data(0x00)
        self.send_data(0x00)

        return 0

    def getbuffer(self, image):
        buf = [0xFF] * (int(self.width / 8) * self.height)
        image_monocolor = image.convert('1')
        imwidth, imheight = image_monocolor.size
        pixels = image_monocolor.load()
        if(imwidth == self.width and imheight == self.height):
            logger.debug("Vertical")
            for y in range(imheight):
                for x in range(imwidth):
                    if pixels[x, y] == 0:
                        buf[int((x + y * self.width) / 8)] &= ~(0x80 >> (x % 8))
        elif(imwidth == self.height and imheight == self.width):
            logger.debug("Horizontal")
            for y in range(imheight):
                for x in range(imwidth):
                    newx = y
                    newy = self.height - x - 1
                    if pixels[x, y] == 0:
                        buf[int((newx + newy * self.width) / 8)] &= ~(0x80 >> (y % 8))
        return buf

    def display(self, image):
        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x24)
        self.send_data2(image)
        self.TurnOnDisplay()

    def Clear(self, color=0xFF):
        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x24)
        for _ in range(self.height * int(self.width / 8)):
            self.send_data(color)
        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0x10)  # Enter deep sleep
        self.send_data(0x01)
        epdconfig.delay_ms(2000)
        epdconfig.module_exit()

### END OF FILE ###
