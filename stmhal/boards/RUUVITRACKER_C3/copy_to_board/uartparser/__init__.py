"""UART parser helper, requires uasyncio"""
import pyb
from uasyncio.core import get_event_loop, sleep

class UARTParser():
    recv_bytes = b''
    EOL = b'\r\n'
    line = b'' # Last detected complete line without EOL marker
    sleep_time = 0.01 # When we have no data sleep this long

    _run = False
    _sol = 0 # Start of line
    _line_cbs = [] # list of 3 value tuples (function, comparevalue, callback)
    _re_cbs = [] # list of 2 value tuples (re, callback)

    def __init__(self, uart):
        self.uart = uart

    def flush(self):
        self.recv_bytes = b''
        line = b''
        _sol = 0

    def parse_buffer(self):
        eolpos = self.recv_bytes.find(self.EOL, self._sol)
        while eolpos > -1:
            # End Of Line detected
            self.line = self.recv_bytes[self._sol:eolpos]
            for cbinfo in self._line_cbs:
                if getattr(self.line, cbinfo[0])(cbinfo[1]):
                    get_event_loop().call_soon(cbinfo[2], self.line, self)
            # Point the start-of-line to next line
            self._sol = eolpos+len(self.EOL)
            # And loop, just in case we have multiple lines in the buffer...
            eolpos = self.recv_bytes.find(self.EOL, self._sol)

        for cbinfo in self._re_cbs:
            match = cbinfo[0](self.recv_bytes)
            if match:
                 get_event_loop().call_soon(cbinfo[1], match, self)

    def add_re_callback(self, regex, cb, method='search'):
        """Adds a regex callback for checking the buffer every time we receive data (this obviously can get a bit expensive), takes the regex as string and callback function.
        Optionally you can specify 'match' instead of search as the method to use for matching. The callback will receive the match object."""
        import ure
        re = ure.compile(regex)
        self._re_cbs.append((getattr(re, method), cb))

    def add_line_callback(self, method, checkstr, cb):
        """Adds a callback for checking full lines, the method can be name of any valid bytearray method but 'startswith' and 'endswith' are probably the good choices.
        The check is performed (and callback will receive  the matched line) with End Of Line removed."""
        # Check that the method is valid
        getattr(self.recv_bytes, method)
        self._line_cbs.append((method, checkstr, cb))

    # TODO: This loop loses bytes for some reason, probably we're too slow even when we do no processing...
    def start(self):
        self._run = True
        while self._run:
            if not self.uart.any():
                yield from sleep(self.sleep_time)
                continue
            recv = self.uart.read(100)
            #recv = self.uart.readchar()
            #if recv < 0:
            if len(recv) == 0:
                # Timed out (it should be impossible though...)
                continue
            self.recv_bytes += recv
            # TODO: We may want to inline the parsing due to cost of method calls
            self.parse_buffer()

    def stop(self):
        self._run = False

