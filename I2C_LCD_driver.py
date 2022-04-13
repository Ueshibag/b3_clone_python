# -*- coding: utf-8 -*-
# Original code found at:
# https://gist.github.com/DenisFromHR/cc863375a6e19dce359d

"""
Compiled, mashed and generally mutilated 2014-2015 by Denis Pleic
Made available under GNU GENERAL PUBLIC LICENSE

# Modified Python I2C library for Raspberry Pi
# as found on http://www.recantha.co.uk/blog/?p=4849
# Joined existing 'i2c_lib.py' and 'lcddriver.py' into a single library
# added bits and pieces from various sources
# By DenisFromHR (Denis Pleic)
# 2015-02-10, ver 0.1

"""
# To connect to the I2C bus in Python we need a library that deals with the details of talking to the Raspberry
# Pi hardware. We will be using the smbus library which is included with Raspbian Linux.
import smbus
from time import sleep

# i2c bus (0 -- original Pi, 1 -- Rev 2 Pi)
I2C_BUS = 0

# LCD Address
ADDRESS = 0x27

global pos_new


class i2c_device:
    def __init__(self, addr, port=I2C_BUS):
        self.addr = addr
        self.bus = smbus.SMBus(port)

    # Write a single command
    def write_cmd(self, cmd):
        self.bus.write_byte(self.addr, cmd)
        sleep(0.0001)

    # Write a command and argument
    def write_cmd_arg(self, cmd, data):
        self.bus.write_byte_data(self.addr, cmd, data)
        sleep(0.0001)

    # Write a block of data
    def write_block_data(self, cmd, data):
        self.bus.write_block_data(self.addr, cmd, data)
        sleep(0.0001)

    # Read a single byte
    def read(self):
        return self.bus.read_byte(self.addr)

    # Read
    def read_data(self, cmd):
        return self.bus.read_byte_data(self.addr, cmd)

    # Read a block of data
    def read_block_data(self, cmd):
        return self.bus.read_block_data(self.addr, cmd)


# commands
LCD_CLEAR_DISPLAY = 0x01
LCD_RETURN_HOME = 0x02
LCD_ENTRY_MODE_SET = 0x04
LCD_DISPLAY_CONTROL = 0x08
LCD_CURSOR_SHIFT = 0x10
LCD_FUNCTION_SET = 0x20
LCD_SET_CGRAM_ADDR = 0x40
LCD_SET_DDRAM_ADDR = 0x80

# flags for display entry mode
LCD_ENTRY_RIGHT = 0x00
LCD_ENTRY_LEFT = 0x02
LCD_ENTRY_SHIFT_INCREMENT = 0x01
LCD_ENTRY_SHIFT_DECREMENT = 0x00

# flags for display on/off control
LCD_DISPLAY_ON = 0x04
LCD_DISPLAY_OFF = 0x00
LCD_CURSOR_ON = 0x02
LCD_CURSOR_OFF = 0x00
LCD_BLINK_ON = 0x01
LCD_BLINK_OFF = 0x00

# flags for display/cursor shift
LCD_DISPLAY_MOVE = 0x08
LCD_CURSOR_MOVE = 0x00
LCD_MOVE_RIGHT = 0x04
LCD_MOVE_LEFT = 0x00

# flags for function set
LCD_8BIT_MODE = 0x10
LCD_4BIT_MODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

# flags for backlight control
LCD_BACKLIGHT = 0x08
LCD_NO_BACKLIGHT = 0x00

En = 0b00000100  # Enable bit
Rw = 0b00000010  # Read/Write bit
Rs = 0b00000001  # Register select bit


class lcd:

    def __init__(self):
        """
        Initializes objects and LCD
        """
        self.lcd_device = i2c_device(ADDRESS)

        self.lcd_write(0x03)
        self.lcd_write(0x03)
        self.lcd_write(0x03)
        self.lcd_write(0x02)

        self.lcd_write(LCD_FUNCTION_SET | LCD_2LINE | LCD_5x8DOTS | LCD_4BIT_MODE)
        self.lcd_write(LCD_DISPLAY_CONTROL | LCD_DISPLAY_ON)
        self.lcd_write(LCD_CLEAR_DISPLAY)
        self.lcd_write(LCD_ENTRY_MODE_SET | LCD_ENTRY_LEFT)
        sleep(0.2)

    def lcd_strobe(self, data):
        """
        Clocks EN to latch command.
        :param data:
        """
        self.lcd_device.write_cmd(data | En | LCD_BACKLIGHT)
        sleep(.0005)
        self.lcd_device.write_cmd(((data & ~En) | LCD_BACKLIGHT))
        sleep(.0001)

    def lcd_write_four_bits(self, data):
        self.lcd_device.write_cmd(data | LCD_BACKLIGHT)
        self.lcd_strobe(data)

    def lcd_write(self, cmd, mode=0):
        """
        Writes a command to LCD.
        :param cmd:
        :param mode:
        """
        self.lcd_write_four_bits(mode | (cmd & 0xF0))
        self.lcd_write_four_bits(mode | ((cmd << 4) & 0xF0))

    def lcd_write_char(self, char_value, mode=1):
        """
        Writes a character to lcd (or character rom) 0x09: backlight | RS=DR < works!
        :param char_value:
        :param mode:
        """
        self.lcd_write_four_bits(mode | (char_value & 0xF0))
        self.lcd_write_four_bits(mode | ((char_value << 4) & 0xF0))

    def lcd_display_string(self, string, line=1, pos=0):
        """
        Displays a string with optional char positioning
        :param string:
        :param line:
        :param pos:
        """
        global pos_new
        if line == 1:
            pos_new = pos
        elif line == 2:
            pos_new = 0x40 + pos
        elif line == 3:
            pos_new = 0x14 + pos
        elif line == 4:
            pos_new = 0x54 + pos

        self.lcd_write(0x80 + pos_new)

        for char in string:
            self.lcd_write(ord(char), Rs)

    def lcd_clear(self):
        """
        Clears LCD and sets cursor to home.
        """
        self.lcd_write(LCD_CLEAR_DISPLAY)
        self.lcd_write(LCD_RETURN_HOME)

    def backlight(self, state):  # for state, 1 = on, 0 = off
        """
        Defines backlight on/off (lcd.backlight(1); off= lcd.backlight(0).
        :param state:
        :return:
        """
        if state == 1:
            self.lcd_device.write_cmd(LCD_BACKLIGHT)
        elif state == 0:
            self.lcd_device.write_cmd(LCD_NO_BACKLIGHT)

    def lcd_load_custom_chars(self, font_data):
        """
        Adds custom characters (0 - 7)
        :param font_data:
        """
        self.lcd_write(0x40)
        for char in font_data:
            for line in char:
                self.lcd_write_char(line)
