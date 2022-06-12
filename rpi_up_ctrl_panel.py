"""
This Python script will be launched on RPi power up by /etc/rc.local

The following Python code refers to the board design described in this KiCad project:
'Raspberry Pi Extension for Upper Control Panel'

The gpiozero library uses Broadcom (BCM) pin numbering for the GPIO pins.
If an LED was attached to “GPIO17” you would specify the pin number as 17 rather than 11 (pin index on GPIO connector).

Selection of the following setBfree settings:

- Volume & Reverb
- Drawbars 1        : display drawbars settings for registration 1
- Drawbars 2        : display drawbars settings for registration 2
- Tuning            :
- Vibrato & Perc.   :
- Analog Model      :
- Leslie Config.    :
- Leslie Filters    :
"""
import os
import sys
import subprocess
import time
import asyncio
import serial
import serial_asyncio

from gpiozero import LED
from gpiozero import Button
from gpiozero import RotaryEncoder

from signal import pause
from drawbars_pos_reader import DrawbarsAsyncReader

from i2c_lcd import Lcd
from signal import signal, SIGINT
from sys import exit


DRAWBARS_TTY = '/dev/ttyACM0'

current_volume_value = 0

# shut down the organ if ON/OFF switch is held OFF (closed) at least 3 seconds
power_on_off_switch = Button(9, hold_time=3.0)

registration_led_1 = LED(6)  # shows registration 1 is active
registration_led_2 = LED(8)  # shows registration 2 is active

registration_sel_1 = Button(5)  # registration 1 selection push button
registration_sel_2 = Button(7)  # registration 2 selection push button

MAX_VOLUME = 16

# volume control of the IQaudio pre-amp; used here to display vol level on LCD
volume_rotary = RotaryEncoder(23, 24, max_steps=MAX_VOLUME, bounce_time=0.10)

MAX_REVERB = 16
# sets the setBfree reverb level
reverb_rotary = RotaryEncoder(25, 26, max_steps=MAX_REVERB, bounce_time=0.10)

ARDUINO_SYNC = b'0\n'

# for synchronous communication with the Arduino (write to Arduino)
sync_serial = None
lcd = None
menu = None


class Menu:
    """
    Manages menus and their submenus on a 2x16 LCD.
    Menus items are listed horizontally and menus items navigation
    is under control of a rotary encoder. The push button of the
    rotary encoder is used to select a menu item.
    """
    def __init__(self, lcd) -> None:
        self.lcd = lcd

    menu = list()
    top = 0
    sub = 0
    count = 1000
    element = None
    isInterrupted = False
    stepScroll = 0
    menu_rotary = RotaryEncoder(0, 1, bounce_time=0.10)  # LCD menus navigation rotary encoder
    menu_push = Button(4)  # LCD menus selection and operation button


    def menus_forward(self):
        print('rotating menu forward')
        self.next_top_element()
        time.sleep(.3)


    def menus_backward(self):
        print('rotating menu backward')
        self.prev_top_element()


    def menus_button_pressed(self):
        print('menus_button_pressed')
        self.next_sub_element()


    def top_element(self, name, element_type, content):
        """
        :param name: 
        :param element_type: 
        :param content: 
        :return Dictionary {Name: Sub: Element_type: Content}: 
        """
        sublist = list()
        subelement = self.sub_element(name, element_type, content)
        sublist.append(subelement)
        return {
            "Name": name,
            "Sub": sublist,
            "Type": element_type,
            "Content": content}

    @staticmethod
    def sub_element(name, element_type, content):
        """
        :param name: 
        :param element_type: 
        :param content: 
        :return: Dictionary {Name: Element_type: Content}: 
        """
        return {
            "Name": name,
            "Type": element_type,
            "Content": content}

    def return_to_top_element(self):
        global element
        self.sub = 0
        self.element = self.menu[self.top]

    def first_top_element(self):
        """
        :return: Element 
        """
        global element
        self.top = 0
        self.sub = 0
        self.element = self.menu[self.top]
        return self.element

    def add_top_element(self, top_element):
        """
        :param top_element: 
        """
        if top_element not in self.menu:
            self.menu.append(top_element)

    @staticmethod
    def add_sub_element(top_element, sub_element):
        """
        :param top_element: 
        :param sub_element: 
        """
        if sub_element not in top_element["Sub"]:
            top_element["Sub"].append(sub_element)

    def return_element(self):
        """
        :return: Element
        """
        global element
        return self.element

    def scroll(self, msg):
        """
        :param lcd: 
        :param msg: 
        """
        global count
        global stepScroll
        if len(msg) > 16:
            self.stepScroll = len(msg) - 16
            if self.count <= 10 & self.stepScroll <= 0:
                self.lcd.scrollDisplayLeft()
                self.stepScroll -= 1
            if self.count > 10:
                print("la")

    def next_top_element(self):
        """
        :param lcd: 
        """
        if len(self.menu) > 0:
            self.top = (self.top + 1) % len(self.menu)
            self.sub = 0
            self.element = self.menu[self.top]
        self.handle_menu()

    def prev_top_element(self):
        """
        :param lcd: 
        """
        if len(self.menu) > 0:
            self.top -= 1
            self.sub = 0
            if self.top < 0:
                self.top = len(self.menu) - 1
            self.element = self.menu[self.top]
        self.handle_menu()

    def next_sub_element(self):
        """
        :param lcd: 
        """
        top_el = self.menu[self.top]
        if len(top_el["Sub"]) > 0:
            self.sub += 1
            if self.sub >= len(top_el["Sub"]):
                self.sub = 0
            self.element = top_el["Sub"][self.sub]
        self.handle_menu()

    def prev_sub_element(self):
        """
        :param lcd: 
        """
        top_el = self.menu[self.top]

        if len(top_el["Sub"]) > 0:
            self.sub -= 1
            if self.sub < 0:
                self.sub = len(top_el["Sub"]) - 1
            self.element = top_el["Sub"][self.sub]
        self.handle_menu()

    def handle_menu(self):
        """
        Executes the command associated with the current menu element.
        """
        msg = ""

        if self.element["Type"] == "VOLUME" or self.element["Type"] == "REVERB":
            self.lcd.set_cursor(0, 0)
            self.lcd.println(self.element["Name"])
            self.lcd.set_cursor(1, 0)
            msg = str(eval(self.element["Content"]))
            return

        elif self.element["Type"] == "STRING":
            self.lcd.set_cursor(0, 0)
            self.lcd.println(self.element["Name"])
            self.lcd.set_cursor(1, 0)
            self.lcd.println(self.element["Content"])
            return

        elif self.element["Type"] == "PYTHON3":
            msg = str(eval(self.element["Content"]))

        elif self.element["Type"] == "BASH":
            msg = subprocess.getoutput(self.element["Content"])

        self.lcd.clear()
        self.lcd.set_cursor(0, 0)
        self.lcd.println(self.element["Name"])
        self.lcd.set_cursor(1, 0)
        self.lcd.println(msg)

    def initialize(self):
        """
        Associates menu rotary encoder and switch actions with callbacks.
        Displays the first menu item.
        """
        global isInterrupted
        self.menu_rotary.when_rotated_clockwise = self.menus_forward
        self.menu_rotary.when_rotated_counter_clockwise = self.menus_backward
        self.menu_push.when_pressed = self.menus_button_pressed

        self.lcd.clear()

        self.first_top_element()

        while True:
            self.handle_menu()
            time.sleep(0.3)
    

def set_registration_1():
    """
    Called when user presses the Registration 1 button.
    """
    print('set_registration_1')
    global sync_serial
    registration_led_1.on()
    registration_led_2.off()
    # tell the Arduino to set drawbars boards registration LED 1 on
    sync_serial.write(b'1\n')


def set_registration_2():
    """
    Called when user presses the Registration 2 button.
    """
    print('set_registration_2')
    global sync_serial
    registration_led_1.off()
    registration_led_2.on()
    # tell the Arduino to set drawbars boards registration LED 2 on
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
    global current_volume_value
    volume_rotary.steps = 0
    volume_rotary.when_rotated_clockwise = volume_up
    volume_rotary.when_rotated_counter_clockwise = volume_down
    current_volume_value = 0


def init_reverb():
    """
    Sets the initial reverb to 0.
    """
    global current_reverb_value
    reverb_rotary.steps = 0
    reverb_rotary.when_rotated_clockwise = reverb_up
    reverb_rotary.when_rotated_counter_clockwise = reverb_down
    current_reverb_value = 0



def on_power_up():
    """
    User powers-up the organ.
    - The LCD shows initialization messages, then the top level menu item.
    - The registration selection is set to 1 (we have two possible registrations).
    - The global volume is set very low.
    - The reverb is set to 0.
    """
    print('on_power_up')
    global menu
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println("Hammond B3 Clone")
    lcd.set_cursor(1, 0)
    lcd.println("=== Welcome! ===")
    time.sleep(3)

    init_registration()
    init_volume()
    init_reverb()

    menu.initialize()


def on_shut_down(rpi_shutdown=True):
    """
    User shuts down the organ with the ON/OFF switch or Ctrl+C in development.

    Args:
        rpi_shutdown (bool, optional): if True, the RPI is shut down, else we only exit this code. Defaults to True.
    """
    print('on_shut_down')
    global lcd, sync_serial

    # turn LCD off
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println("===== Bye =====")
    time.sleep(3)
    lcd.clear()

    # turn registration buttons LEDs off
    registration_led_1.off()
    registration_led_2.off()

    # turn drawbars boards LEDs off
    # TODO: modify Arduino code to accept this cmd
    sync_serial.write(b'3\n')

    if rpi_shutdown:
        os.system("sudo shutdown -h now")
    else:
        exit(0)


def handler(signal_received, frame):
    """
    Handles system or user interrupts.
    """
    print('SIGINT or CTRL-C detected. Exiting.')
    on_shut_down(rpi_shutdown=False)


def display_volume_value():
    global current_volume_value
    volume_rotary.steps = current_volume_value
    for col in range(current_volume_value + 1):
        lcd.set_cursor(1, col)
        lcd.println('\u00db')


def display_reverb_value():
    global current_reverb_value
    reverb_rotary.steps = current_reverb_value
    for col in range(current_reverb_value + 1):
        lcd.set_cursor(1, col)
        lcd.println('\u00db')


def add_menu_items(menu: Menu):
    """
    Adds menu items to the menu; some of them have sub-items.

    Args:
        menu (Menu): an instance of the Menu class we add items to
    """
    top_volume = menu.top_element("<    Volume    >", "STRING", "                ")
    top_reverb = menu.top_element("<    Reverb    >", "STRING", "                ")
    top3 = menu.top_element("<   Drawbars   >", "STRING", "                ")
    top4 = menu.top_element("<    Tuning    >", "STRING", "                ")
    top5 = menu.top_element("<    Vibrato   >", "STRING", "                ")
    top6 = menu.top_element("<  Percussions >", "STRING", "                ")
    top7 = menu.top_element("< Analog Model >", "STRING", "                ")
    top8 = menu.top_element("<    Leslie    >", "STRING", "                ")
    top9 = menu.top_element("<    System    >", "STRING", "                ")
    top10 = menu.top_element("<    Network   >", "STRING", "                ")

    sub_volume = menu.sub_element("Volume:         ", "VOLUME",  "display_volume_value()")

    sub_reverb = menu.sub_element("Reverb:         ", "REVERB",  "display_reverb_value()")

    sub91 = menu.sub_element("System>CPU", "PYTHON3",
                             "str(eval('exec(\"import psutil\") or psutil.cpu_percent()')) + '%'")

    sub92 = menu.sub_element("System>CPU-Temp.", "BASH",
                            "vcgencmd measure_temp | sed 's/temp=//g'")

    sub93 = menu.sub_element("System>RAM", "PYTHON3",
                             "str(eval('exec(\"import psutil\") or psutil.virtual_memory()[2]')) + '% used'")

    sub101 = menu.sub_element("Net.>Signal Lev", "BASH",
                             "iwconfig wlan0 | awk -F'[ =]+' '/Signal level/ {print $7}' | cut -d/ -f1")
                             
    sub102 = menu.sub_element("Net.>SSID", "BASH",
                             "iwconfig wlan0 | grep 'ESSID:' | awk '{print $4}' | sed 's/ESSID://g' | sed 's/\"//g'")

    sub103 = menu.sub_element("Net.>Internet", "BASH",
                             "ping -q -w 1 -c 1 `ip r | grep default | cut -d ' ' -f 3` > /dev/null && echo ok || echo error")
    
    # Adding elements to the menu
    menu.add_top_element(top_volume)
    menu.add_top_element(top_reverb)
    menu.add_top_element(top3)
    menu.add_top_element(top4)
    menu.add_top_element(top5)
    menu.add_top_element(top6)
    menu.add_top_element(top7)
    menu.add_top_element(top8)
    menu.add_top_element(top9)
    menu.add_top_element(top10)

    menu.add_sub_element(top_volume, sub_volume)
    menu.add_sub_element(top_reverb, sub_reverb)

    menu.add_sub_element(top9, sub91)
    menu.add_sub_element(top9, sub92)
    menu.add_sub_element(top9, sub93)

    menu.add_sub_element(top10, sub101)
    menu.add_sub_element(top10, sub102)
    menu.add_sub_element(top10, sub103)


def volume_up():
    global current_volume_value
    lcd_column = volume_rotary.steps
    current_volume_value = volume_rotary.steps
    lcd.set_cursor(1, lcd_column)
    lcd.println('\u00db')


def volume_down():
    global current_volume_value
    lcd_column = volume_rotary.steps
    current_volume_value = volume_rotary.steps
    lcd.set_cursor(1, lcd_column)
    lcd.println('\u00db')

    for _ in range(lcd_column + 1, 16):
        lcd.println(' ')

def reverb_up():
    global current_reverb_value
    lcd_column = reverb_rotary.steps
    current_reverb_value = reverb_rotary.steps
    lcd.set_cursor(1, lcd_column)
    lcd.println('\u00db')


def reverb_down():
    global current_reverb_value
    lcd_column = reverb_rotary.steps
    current_reverb_value = reverb_rotary.steps
    lcd.set_cursor(1, lcd_column)
    lcd.println('\u00db')

    for _ in range(lcd_column + 1, 16):
        lcd.println(' ')


def main():
    """
    Everything starts here.
    """
    global lcd, sync_serial, menu

    power_on_off_switch.when_held = on_shut_down

    # initialize the organ if ON/OFF switch is set ON (open)
    power_on_off_switch.when_deactivated = on_power_up

    lcd = Lcd(bus=1, addr=0x3c, rows=2, cols=16)

    menu = Menu(lcd)
    add_menu_items(menu)

    drawbars_reader = DrawbarsAsyncReader()

    # for synchronous write to the Arduino
    sync_serial = serial.Serial(DRAWBARS_TTY, 115200, timeout=1)
    on_power_up()

    loop = asyncio.get_event_loop()
    drawbars_reader_coroutine = serial_asyncio.create_serial_connection(
        loop, lambda: drawbars_reader, DRAWBARS_TTY, baudrate=115200)
    asyncio.ensure_future(drawbars_reader_coroutine)
    loop.run_forever()


if __name__ == '__main__':

    # tell Python to run the handler() function when SIGINT or CTRL+C is received
    signal(SIGINT, handler)

    main()

    # keep the program listening for events
    pause()
