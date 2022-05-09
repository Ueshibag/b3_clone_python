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
from gpiozero import Button
from gpiozero import LED
from signal import pause
from gpiozero import RotaryEncoder
from i2c_lcd import Lcd
from signal import signal, SIGINT
from sys import exit

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


def set_registration_1():
    """
    Called when user presses the Registration 1 button.
    """
    registration_led_1.on()
    registration_led_2.off()
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println("Registration 1")


def set_registration_2():
    """
    Called when user presses the Registration 2 button.
    """
    registration_led_1.off()
    registration_led_2.on()
    lcd.clear()
    lcd.set_cursor(1, 0)
    lcd.println("Registration 2")


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
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println("Hammond B3 Clone")
    lcd.set_cursor(1, 0)
    lcd.println("=== Welcome! ===")
    time.sleep(3)

    init_registration()
    init_volume()
    init_reverb()


def on_shut_down():
    """
    User shuts down the organ.
    """
    global lcd
    lcd.clear()
    lcd.println("===== Bye =====")
    time.sleep(3)
    os.system("sudo shutdown -h now")


def handler(signal_received, frame):
    # Handle any cleanup here
    print('SIGINT or CTRL-C detected. Exiting.')
    lcd.clear()
    exit(0)


if __name__ == '__main__':
    # tell Python to run the handler() function when SIGINT is received
    signal(SIGINT, handler)

    # power_on_off_switch.when_held = on_shut_down

    # initialize the organ if ON/OFF switch is set ON (open)
    # power_on_off_switch.when_deactivated = on_power_up

    # for test purpose, while I am working on table
    on_power_up()

    # keep the program listening for the different events
    pause()
