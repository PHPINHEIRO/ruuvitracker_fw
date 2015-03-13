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
    _line_cbs = {} # map of 3 value tuples (function, comparevalue, callback)
    _re_cbs = {} # map of 2 value tuples (re, callback)

    def __init__(self, uart):
        self.uart = uart

    def flush(self):
        self.recv_bytes = b''
        self.line = b''
        self._sol = 0

    def flushto(self, pos):
        self.recv_bytes = self.recv_bytes[pos:]
        if pos > self._sol:
            self.line = b''
            self._sol = 0

    def parse_buffer(self):
        eolpos = self.recv_bytes.find(self.EOL, self._sol)
        while eolpos > -1:
            # End Of Line detected
            self.line = self.recv_bytes[self._sol:eolpos]
            flushnow = False
            for cbid in self._line_cbs:
                cbinfo =  self._line_cbs[cbid]
                if getattr(self.line, cbinfo[0])(cbinfo[1]):
                    # PONDER: Maybe we do not want to pass the parser reference around...
                    if (cbinfo[2](self.line, self)):
                        flushnow = True
            if flushnow:
                self.flushto(eolpos+len(self.EOL))
            else:
                # Point the start-of-line to next line
                self._sol = eolpos+len(self.EOL)
            # And loop, just in case we have multiple lines in the buffer...
            eolpos = self.recv_bytes.find(self.EOL, self._sol)

        # The flushing strategy here won't work, we always end up flushign too much
        # Maybe we should only parse in line context and leave multiline parsing for the 
        # "raw mode" consumer to do as they deem fit.
        for cbid in self._re_cbs:
            cbinfo =  self._re_cbs[cbid]
            match = cbinfo[0](self.recv_bytes)
            flushnow = False
            if match:
                # PONDER: Maybe we do not want to pass the parser reference around...
                if (cbinfo[1](match, self)):
                    flushnow = True
            if flushnow:
                self.flush()

    def add_re_callback(self, cbid, regex, cb, method='search'):
        """Adds a regex callback for checking the buffer every time we receive data (this obviously can get a bit expensive), takes the regex as string and callback function.
        Optionally you can specify 'match' instead of search as the method to use for matching. The callback will receive the match object and reference to this parser. Return True from the callback to flush the buffer"""
        import ure
        # Compile the regex
        re = ure.compile(regex)
        # And add the the callback list
        self._re_cbs[cbid] = (getattr(re, method), cb)

    def del_re_callback(self, cbid):
        """Removes a regex callback"""
        if cbid in self._re_cbs:
            del(self._re_cbs[cbid])
            return True
        return False

    def add_line_callback(self, cbid, method, checkstr, cb):
        """Adds a callback for checking full lines, the method can be name of any valid bytearray method but 'startswith' and 'endswith' are probably the good choices.
        The check is performed (and callback will receive  the matched line) with End Of Line removed and reference to this parser. Return True from the callback to flush the buffer"""
        # Check that the method is valid
        getattr(self.recv_bytes, method)
        # And add the the callback list
        self._line_cbs[cbid] = (method, checkstr, cb)

    def del_line_callback(self, cbid):
        """Removes a line callback"""
        if cbid in self._line_cbs:
            del(self._line_cbs[cbid])
            return True
        return False

    def start(self):
        self._run = True
        while self._run:
            if not self.uart.any():
                yield from sleep(self.sleep_time)
                continue
            recv = self.uart.read(100)
            if len(recv) == 0:
                # Timed out (it should be impossible though...)
                continue
            self.recv_bytes += recv
            # TODO: We may want to inline the parsing due to cost of method calls
            self.parse_buffer()

    def stop(self):
        self._run = False

