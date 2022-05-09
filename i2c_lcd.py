import smbus
from time import sleep


def delay_milli_seconds(time):
    sleep(time / 1000.0)


def delay_micro_seconds(time):
    sleep(time / 1000000.0)


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
LCD_ENTRY_RIGHT = 0x02
LCD_ENTRY_LEFT = 0x00
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
LCD_I2C_MODE = 0x10
LCD_8BIT_MODE = 0x10
LCD_4BIT_MODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

LCD_CHR = 1  # Mode - Sending data
LCD_CMD = 0  # Mode - Sending command
    

class Lcd:
    """
    Supports I2C communication between Raspberry PI and
    MIDAS MC21605C6W-SPTLYI-V2 2x16 LCD with RW1063 controller.
    """
    row_offsets = [0x00, 0x40, 0x14, 0x54]
    
    def __init__(self, bus=1, addr=0x20, rows=2, cols=16):
        """
        Initializes the Lcd object.
        :param bus: I2C bus number
        :param addr: I2C device address
        :param rows: LCD number of rows
        :param cols: LCD number of columns
        """
        self.bus_num = bus
        self.bus = smbus.SMBus(self.bus_num)
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self._init_display()

    def _init_display(self):
        """
        LCD RW1063 controller initialization sequence.
        """
        self.bus.write_byte_data(self.addr, LCD_CMD, LCD_FUNCTION_SET | LCD_I2C_MODE)
        delay_milli_seconds(1)
        self.bus.write_byte_data(self.addr, LCD_CMD, LCD_FUNCTION_SET | LCD_I2C_MODE)
        delay_milli_seconds(1)
        self.bus.write_byte_data(self.addr, LCD_CMD, LCD_DISPLAY_CONTROL | LCD_DISPLAY_OFF | LCD_CURSOR_OFF |
                                 LCD_BLINK_OFF)
        delay_milli_seconds(1)
        self.bus.write_byte_data(self.addr, LCD_CMD, LCD_ENTRY_MODE_SET | LCD_MOVE_RIGHT)
        delay_milli_seconds(1)
        self.bus.write_byte_data(self.addr, LCD_CHR, 0x34)
        delay_milli_seconds(10)
        self.bus.write_byte_data(self.addr, LCD_CHR, 0x02)
        delay_milli_seconds(100)
        self.bus.write_byte_data(self.addr, LCD_CHR, 0x06)
        delay_milli_seconds(100)
        self.bus.write_byte_data(self.addr, LCD_CHR, 0x16)
        delay_milli_seconds(100)
        self.bus.write_byte_data(self.addr, LCD_CHR, 0x08)
        delay_milli_seconds(100)
        self.bus.write_byte_data(self.addr, LCD_CHR, 0x08)
        delay_milli_seconds(100)
        self.bus.write_byte_data(self.addr, LCD_CMD, LCD_FUNCTION_SET | LCD_I2C_MODE | LCD_2LINE | LCD_5x8DOTS)
        delay_milli_seconds(1)
        self.bus.write_byte_data(self.addr, LCD_CMD, LCD_DISPLAY_CONTROL | LCD_DISPLAY_ON | LCD_CURSOR_OFF |
                                 LCD_BLINK_OFF)
        delay_milli_seconds(1)
        self.clear()

    def println(self, line: str):
        """
        Displays a line of text from the current cursor position.
        :param line: string of characters to be displayed
        """
        for char in line:
            self.write_byte(ord(char), char_mode=True)

    def write_byte(self, data, char_mode=False):
        """
        Writes a data or command byte to the LCD.
        :param data: byte to be written
        :param char_mode: in character mode if true, else in command mode
        """
        if char_mode:
            self.bus.write_byte_data(self.addr, 0x40, data)
        else:
            self.bus.write_byte_data(self.addr, 0x00, data)

    def clear(self):
        """
        Clears the display.
        """
        self.write_byte(LCD_CLEAR_DISPLAY)
        delay_micro_seconds(3000)

    def home(self):
        """
        Returns cursor to home position.
        """
        self.write_byte(LCD_RETURN_HOME)
        delay_micro_seconds(3000)
        
    def set_cursor(self, row: int, col: int):
        """
        Sets the cursor to the specified location.
        :param row: cursor row
        :param col: cursor column
        """
        self.write_byte(LCD_SET_DDRAM_ADDR | (col + self.row_offsets[row]))
        
        
if __name__ == "__main__":

    lcd = Lcd(bus=1, addr=0x3c, rows=2, cols=16)

    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.println('0123456789ABCDEF')
    lcd.set_cursor(1, 0)
    lcd.println('FEDCBA9876543210')
    sleep(4)
    lcd.clear()
