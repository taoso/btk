try:
    from gi.repository import GObject as gobject
except ImportError:
    import gobject

import evdev as ev
import keymap
import os
import struct

class Device:
    def __init__(self, dev_paths, report_id):
        self.devs = [ev.InputDevice(dev_path) for dev_path in dev_paths]
        self.state = [
            0xA1, # This is an input report by USB
            report_id, # Report Id assigned for Mouse, in HID Descriptor
        ]

    def register_intr_sock(self, sock):
        self.sock = sock
        for dev in self.devs:
            gobject.io_add_watch(dev, gobject.IO_IN, self.ev_cb)

class Mouse(Device):
    def __init__(self, dev_path, report_id = 0x01):
        Device.__init__(self, dev_path, report_id)

        self.state.extend([
            # (D7 being the first element, D0 being last)
            [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
            0x00, # X
            0x00, # Y
            0x00, # Wheel
        ])

    def update_state(self):
        event = self.event
        # this would reset all buttons to unpressed on each event
        # self.state[2] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.state[3] = 0
        self.state[4] = 0
        self.state[5] = 0
        if event.code == ev.ecodes.REL_X:
            self.state[3] = event.value
        elif event.code == ev.ecodes.REL_Y:
            self.state[4] = event.value
        elif event.code == ev.ecodes.REL_WHEEL:
            self.state[5] = event.value
        # I didn't see any ABS_MISC codes, and it looks
        # like these may have been destined for buttons
        #elif event.code == ev.ecodes.ABS_MISC:
        #    if event.value == 1:
        #        self.state[2][7] = 1
        #    elif event.value == 2:
        #        self.state[2][6] = 1
        #    elif event.value == 4:
        #        self.state[2][5] = 1
        elif event.code == ev.ecodes.BTN_LEFT:
            self.state[2][7] = event.value
        elif event.code == ev.ecodes.BTN_MIDDLE:
            self.state[2][5] = event.value
        elif event.code == ev.ecodes.BTN_RIGHT:
            self.state[2][6] = event.value
        else:
            print("unhandled code:")
            print(event.code)
            print("value:")
            print(event.value)
            print("event:")
            print(event.__repr__)

    def ev_cb(self, dev, io_type):
        event = dev.read_one()
        if event.type in [ev.ecodes.EV_REL,
                          ev.ecodes.EV_ABS,
                          ev.ecodes.EV_KEY
                      ]:
            self.event = event
            self.update_state()
            self.sock.send(self.to_bstr())
        elif event.type == ev.ecodes.EV_SYN:
            pass
        elif event.type == ev.ecodes.EV_MSC:
            # not sure what MSC info from the mouse does
            pass
        else:
            print('unhandled mouse')
            print("code:")
            print(event.code)
            print("value:")
            print(event.value)
            print("event:")
            print(event.__repr__)

        return True

    def to_bstr(self):
        # Convert the hex array to a string
        hex_str = b""
        for element in self.state[:3]:
            if type(element) is list:
                # This is our bit array - convert it to a single byte represented
                # as a char
                bin_str = ""
                for bit in element:
                    bin_str += str(bit)
                hex_str += struct.pack("B", int(bin_str, 2))
            else:
                # This is a hex value - we can convert it straight to a char
                hex_str += struct.pack("B", element)

        for element in self.state[3:]:
            hex_str += struct.pack("b", element)

        return hex_str

class Keyboard(Device):
    def __init__(self, dev_path, report_id = 0x02):
        Device.__init__(self, dev_path, report_id)

        self.state.extend([
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
        ])

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
        if event.type == ev.ecodes.EV_KEY and event.value < 2:
            self.event = event
            self.update_state()
            self.sock.send(self.to_bstr())

        return True

    def to_bstr(self):
        # Convert the hex array to a string
        hex_str = b""
        for element in self.state:
            if type(element) is list:
                # This is our bit array - convert it to a single byte represented
                # as a char
                bin_str = ""
                for bit in element:
                    bin_str += str(bit)
                hex_str += struct.pack("B", int(bin_str, 2))
            else:
                # This is a hex value - we can convert it straight to a char
                hex_str += struct.pack("B", element)

        return hex_str
