import asyncio


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
                pass # TODO: display drawbar data

    def connection_lost(self, exc):
        self.transport.loop.stop()

    def pause_writing(self):
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
