"""
This Python script will be launched on RPi power up by /etc/rc.local

The following Python code refers to the board design described in this KiCad project:
'Raspberry Pi Extension for Upper Control Panel'

The gpiozero library uses Broadcom (BCM) pin numbering for the GPIO pins.
If an LED was attached to “GPIO17” you would specify the pin number as 17 rather than 11 (pin index on GPIO connector).

Selection of the following setBfree settings:

- Drawbars 1        : display drawbars settings for registration 1
- Drawbars 2        : display drawbars settings for registration 2
- Tuning            :
- Vibrato & Perc.   :
- Analog Model      :
- Leslie Config.    :
- Leslie Filters    :
"""
import os
import time
import asyncio
import serial

import serial_asyncio
from gpiozero import Button
from gpiozero import LED
from signal import pause
from gpiozero import RotaryEncoder
from i2c_lcd import Lcd
from signal import signal, SIGINT
from sys import exit

DRAWBARS_TTY = '/dev/ttyACM0'

# shut down the organ if ON/OFF switch is held OFF (closed) at least 3 seconds
power_on_off_switch = Button(9, hold_time=3.0)

lcd = Lcd(bus=1, addr=0x3c, rows=2, cols=16)

registration_led_1 = LED(6)  # shows registration 1 is active
registration_led_2 = LED(8)  # shows registration 2 is active

registration_sel_1 = Button(5)  # registration 1 selection push button
registration_sel_2 = Button(7)  # registration 2 selection push button

menus_rotary = RotaryEncoder(0, 1)  # LCD menus navigation rotary encoder
menus_push = Button(4)  # LCD menus selection and operation button

# volume control of the IQaudio pre-amp; used here to display vol level on LCD
MAX_VOLUME = 50
volume_rotary = RotaryEncoder(23, 24, max_steps=MAX_VOLUME)

MAX_REVERB = 50
reverb_rotary = RotaryEncoder(25, 26, max_steps=MAX_REVERB)  # sets the setBfree reverb level

ARDUINO_SYNC = b'0\n'


def display_drawbar_position(drawbar):
    """
    Displays drawbars positions values (0 to 8) to LCD.
    :param drawbar: 3-byte drawbar information:
                    - 0xB0 | MIDI channel
                    - drawbar index (70 to 78 for upper keyboard)
                    - drawbar position
    """
    lcd_row = 0
    lcd_col = 0
    lcd.set_cursor(0, 0)
    lcd.println('Upper: ')
    lcd.set_cursor(1, 0)
    lcd.println('Lower: ')

    # associate drawbar position value sent by the Arduino with index value from 0 to 8 to be displayed by LCD
    position_dict = {127: '0', 110: '1', 92: '2', 79: '3', 63: '4', 47: '5', 31: '6', 15: '7', 0: '8'}
    drawbar_position = position_dict[drawbar[2]]

    if drawbar[0] == 0xb0 or drawbar[0] == 0xb3:
        lcd_row = 0  # upper kb / registration 1 or 2
        lcd_col = drawbar[1] - 70 + 7

    elif drawbar[0] == 0xb1 or drawbar[0] == 0xb4:
        lcd_row = 1  # lower kb / registration 1 or 2
        lcd_col = 0

    lcd.set_cursor(lcd_row, lcd_col)
    lcd.println(drawbar_position)
    print('display_drawbar_position ' + drawbar_position)


class DrawbarsAsyncReader(asyncio.Protocol):
    """
    Asynchronously reads drawbars information from the Arduino.
    """
    def __init__(self):
        self.transport = None
        self.buf = bytes()

    def connection_made(self, tport):
        self.transport = tport
        tport.serial.rts = False  # You can manipulate Serial object via transport

    def data_received(self, data):
        """
        Stores characters until a newline is received, then displays drawbars positions.
        :param data: stream of MIDI CC messages sent by the Arduino and separated by NL
        """
        print('data_received : ' + str(data))
        self.buf += data

        if b'\n' in self.buf:
            lines = self.buf.split(b'\n')
            self.buf = lines[-1]  # whatever was left over
            for draw_bar in lines[:-1]:
                display_drawbar_position(draw_bar)

    def connection_lost(self, exc):
        self.transport.loop.stop()

    def pause_writing(self):
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())


def set_registration_1():
    """
    Called when user presses the Registration 1 button.
    """
    print('set_registration_1')
    registration_led_1.on()
    registration_led_2.off()
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println("Registration 1")
    sync_serial.write(b'1\n')


def set_registration_2():
    """
    Called when user presses the Registration 2 button.
    """
    print('set_registration_2')
    registration_led_1.off()
    registration_led_2.on()
    lcd.clear()
    lcd.set_cursor(1, 0)
    lcd.println("Registration 2")
    sync_serial.write(b'2\n')


def init_registration():
    """
    Initializes registration LEDs state and buttons actions.
    """
    registration_sel_1.when_pressed = set_registration_1
    registration_sel_2.when_pressed = set_registration_2
    set_registration_1()


def init_volume():
    """
    Sets the initial volume to a low, still audible value.
    """
    set_volume(int(MAX_VOLUME / 10))


def init_reverb():
    """
    Sets the initial reverb to a low value.
    """
    set_reverb(int(MAX_REVERB / 10))


def set_volume(steps: int):
    volume_rotary.steps = steps


def set_reverb(steps: int):
    reverb_rotary.steps = steps


def on_power_up():
    """
    User powers-up the organ.
    - The LCD shows initialization messages, then the top level menu item.
    - The registration selection is set to 1 (we have two possible registrations).
    - The global volume is set to 10%.
    - The reverb is set to 0.
    """
    print('on_power_up')
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println("Hammond B3 Clone")
    lcd.set_cursor(1, 0)
    lcd.println("=== Welcome! ===")
    time.sleep(3)

    init_registration()
    init_volume()
    init_reverb()


def on_shut_down(rpi_shutdown=True):
    """
    User shuts down the organ.
    """
    print('on_shut_down')
    global lcd
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println("===== Bye =====")
    time.sleep(3)
    lcd.clear()

    if rpi_shutdown:
        os.system("sudo shutdown -h now")
    else:
        exit(0)


def handler(signal_received, frame):
    print('SIGINT or CTRL-C detected. Exiting.')
    on_shut_down(rpi_shutdown=False)


if __name__ == '__main__':
    # tell Python to run the handler() function when SIGINT or CTRL-C is received
    signal(SIGINT, handler)

    power_on_off_switch.when_held = on_shut_down

    # initialize the organ if ON/OFF switch is set ON (open)
    power_on_off_switch.when_deactivated = on_power_up

    sync_serial = serial.Serial(DRAWBARS_TTY, 115200, timeout=1)  # for synchronous write to the Arduino
    on_power_up()

    loop = asyncio.get_event_loop()
    drawbars_reader = serial_asyncio.create_serial_connection(loop, DrawbarsAsyncReader, DRAWBARS_TTY, baudrate=115200)
    asyncio.ensure_future(drawbars_reader)
    loop.run_forever()

    # keep the program listening for the different events
    pause()
