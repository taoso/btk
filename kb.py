import gobject
import evdev as ev
import keymap
import os
from IPython import embed
import bluetooth as bt

class Keyboard:
    fd = -1
    def __init__(self, dev_path='/dev/input/event3'):
        self.dev = ev.InputDevice(dev_path)

        self.state = [
            0xA1, # This is an input report
            0x01, # Usage report = Keyboard
            # Bit array for Modifier keys
            # (D7 being the first element, D0 being last)
            [
                0,  # Right GUI - (usually the Windows key)
                0,  # Right ALT
                0,  # Right Shift
                0,  # Right Control
                0,  # Left GUI - (again, usually the Windows key)
                0,  # Left ALT
                0,  # Left Shift
                0,  # Left Control
            ],
            0x00, # Vendor reserved
            0x00, # Rest is space for 6 keys
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]

    def register_intr_sock(self, sock):
        self.sock = sock
        gobject.io_add_watch(self.dev, gobject.IO_IN, self.ev_cb)

    def update_state(self):
        event = self.event
        evdev_code = ev.ecodes.KEY[event.code]
        modkey_element = keymap.modkey(evdev_code)
        if modkey_element > 0:
            # Need to set one of the modifier bits
            if self.state[2][modkey_element] == 0:
                self.state[2][modkey_element] = 1
            else:
                self.state[2][modkey_element] = 0
        else:
            # Get the hex keycode of the key
            hex_key = keymap.convert(ev.ecodes.KEY[event.code])
            # Loop through elements 4 to 9 of the input report structure
            for i in range (4, 10):
                if self.state[i] == hex_key and event.value == 0:
                    # Code is 0 so we need to depress it
                    self.state[i] = 0x00
                elif self.state[i] == 0x00 and event.value == 1:
                    # If the current space is empty and the key is being pressed
                    self.state[i] = hex_key
                    break

    def ev_cb(self, dev, io_type):
        event = dev.read_one()
        
        if event.__class__ != ev.events.InputEvent:
            embed()

        if event.type == ev.ecodes.EV_KEY and event.value < 2:
            self.event = event
            self.update_state()

            try:
                self.sock.send(self.to_bstr())
            except bt.BluetoothError as e:
                if 'Connection reset by peer' in e.message:
                    print 'We lost our host!!!'
                elif 'Transport endpoint is not connected' in e.message:
                    print 'We should reconnect!!!'
                else:
                    print(e, e.message)
            except Exception as e:
                print(e, e.message)

        return True

    def to_bstr(self):
        # Convert the hex array to a string
        hex_str = ""
        for element in self.state:
            if type(element) is list:
                # This is our bit array - convert it to a single byte represented
                # as a char
                bin_str = ""
                for bit in element:
                    bin_str += str(bit)
                hex_str += chr(int(bin_str, 2))
            else:
                # This is a hex value - we can convert it straight to a char
                hex_str += chr(element)

        return hex_str


if __name__ == '__main__':
    kb = Keyboard('/dev/input/event3')
    kb.register_cb(open('/tmp/kb', 'w').fileno())

    gobject.MainLoop().run()
