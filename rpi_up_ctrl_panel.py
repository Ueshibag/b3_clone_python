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

import I2C_LCD_driver

# shut down the organ if ON/OFF switch is held OFF (closed) at least 3 seconds
power_on_off_switch = Button(9, hold_time=3.0)

lcd = I2C_LCD_driver.lcd()  # 16 chars / 2 lines LCD

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


def init_lcd():
    """
    Clears the LCD, then displays a welcome message for a few seconds.
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("=== Welcome ===")
    time.sleep(3)


def init_registration():
    """
    Initializes registration LEDs state.
    """
    registration_led_1.on()
    registration_led_2.off()


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
    init_lcd()
    init_registration()
    init_volume()
    init_reverb()


def on_shut_down():
    """
    User shuts down the organ.
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("===== Bye =====")
    time.sleep(3)
    os.system("sudo shutdown -h now")


if __name__ == '__main__':

    power_on_off_switch.when_held = on_shut_down

    # initialize the organ if ON/OFF switch is set ON (open)
    power_on_off_switch.when_deactivated = on_power_up

    # keep the program listening for the different events
    pause()
