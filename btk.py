#! /usr/bin/env python

from __future__ import print_function

import errno
import glob
import os
import struct
import sys
import time
import uuid

from gi.repository import GLib
from pydbus import SystemBus
import bluetooth as bt

from dbus import Server
from inputdev import Keyboard, Mouse

keyboard_dev_paths = glob.glob('/dev/input/by-path/*event-kbd')
mouse_dev_paths = glob.glob('/dev/input/by-path/*event-mouse')

# mouse button event will be fired from keyboard_dev_paths
mouse = Mouse(mouse_dev_paths + keyboard_dev_paths)
keyboard = Keyboard(keyboard_dev_paths)

BUF_SIZE = 1024
PSM_CTRL = 0x11
PSM_INTR = 0x13

HIDP_HEADER_PARAM_MASK = 0x0f
HIDP_HEADER_TRANS_MASK = 0xf0

HIDP_HSHK_ERR_UNKNOWN = 0x0e
HIDP_HSHK_SUCCESSFUL = 0x00

HIDP_TRANS_DATA = 0xa0
HIDP_TRANS_HANDSHAKE = 0x00
HIDP_TRANS_SET_PROTOCOL = 0x70

class HIDConnection:
    ctrl_fd = -1
    intr_sock = None
    ctrl_io_id = None
    intr_id_id = None
    kb = None

    def __init__(self, ctrl_fd):
        self.ctrl_fd = ctrl_fd

        self.ctrl_io_id = GLib.io_add_watch(
            self.ctrl_fd,
            GLib.IO_IN,
            self.ctrl_data_cb
        )

    def hello(self):
        print('------hello-------')
        os.write(self.ctrl_fd, b'\xa1\x13\x03')
        os.write(self.ctrl_fd, b'\xa1\x13\x02')

        time.sleep(1)

    def ctrl_data_cb(self, fd, io_type):
        print('type: ' + str(io_type))
        data = os.read(fd, BUF_SIZE)
        if len(data) == 0:
            print('someone disconnected')
            # I get this when we disconnect
            return False

        handshake = HIDP_TRANS_HANDSHAKE
        if data.__class__ == str:
            print('Received ' + data.__repr__())
            if data[0] == '\x03':
                print('set protocol')
                handshake |= HIDP_HSHK_SUCCESSFUL
                os.write(fd, str(handshake))
                return True

        msg_type = ord(data[0]) & HIDP_HEADER_TRANS_MASK

        if msg_type & HIDP_TRANS_SET_PROTOCOL:
            print('set protocol')
            handshake |= HIDP_HSHK_SUCCESSFUL
            os.write(fd, struct.pack("b", handshake))
            return True

        if msg_type & HIDP_TRANS_DATA:
            print('data')
            return True

        print('unknown error')
        handshake |= HIDP_HSHK_ERR_UNKNOWN
        os.write(fd, struct.pack("b", handshake))
        return True

    def register_intr_socks(self, sock):
        self.hello()
        self.intr_sock = sock
        mouse.register_intr_sock(self.intr_sock)
        keyboard.register_intr_sock(self.intr_sock)

    def close(self):
        pass

class HIDProfile(Server):
    '''
<node>
	<interface name='org.bluez.Profile1'>
		<method name='Release'></method>
		<method name='RequestDisconnection'>
			<arg type='o' name='device' direction='in'/>
		</method>
		<method name='NewConnection'>
			<arg type='o' name='device' direction='in'/>
			<arg type='h' name='fd' direction='in'/>
			<arg type='a{sv}' name='fd_properties' direction='in'/>
		</method>
	</interface>
</node>
    '''
    conns = {}
    sock = None

    def __init__(self, bus, path, sock):
        Server.__init__(self, bus, path)
        self.sock = sock

    def Release(self):
        print("Release")
        self.quit()

    def RequestDisconnection(self, device):
        print('RequestDisconnection (%s)' % device)
        self.conns.pop(device).close()

    def NewConnection(self, device, fd, fd_properties):
        print("New control connection (%s, %d, %s)" % (device, fd, fd_properties))
        self.conns[device] = HIDConnection(fd)

        def new_intr_conn(ssock, ip_type):
            sock, info = ssock.accept()
            print("interrupt connection:", info)
            self.conns[device].register_intr_socks(sock)
            return False

        GLib.io_add_watch(self.sock, GLib.IO_IN, new_intr_conn)

def loop():
    bus = SystemBus()
    bus.own_name('net.lvht.btk')
    obj_path = '/net/lvht/btk/HIDProfile'

    sock = bt.BluetoothSocket(bt.L2CAP)
    sock.setblocking(False)
    try:
        sock.bind(('', PSM_INTR))
    except:
        print("For bluez5 add --noplugin=input to the bluetoothd commandline")
        print("Else there is another application running that has it open.")
        sys.exit(errno.EACCES)
    sock.listen(1)

    profile = HIDProfile(bus.con, obj_path, sock)

    opts = {
        "PSM": GLib.Variant.new_uint16(PSM_CTRL),
        "ServiceRecord": GLib.Variant.new_string(open('sdp_record.xml', 'r').read()),
        "RequireAuthentication": GLib.Variant.new_boolean(True),
        "RequireAuthorization": GLib.Variant.new_boolean(False),
    }
    manager = bus.get('org.bluez')['.ProfileManager1']
    manager.RegisterProfile(obj_path, str(uuid.uuid4()), opts)

    profile.run()

if __name__ == '__main__':
    loop()
