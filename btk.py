import dbus
import dbus.mainloop.glib
import dbus.service

try:
    import gobject
except ImportError:
    from gi.repository import GObject as gobject

import kb
import os
import bluetooth as bt
import uuid
import time
import glob


mainloop = None
keyboard = kb.Keyboard(glob.glob('/dev/input/by-id/usb*event-kbd')[0])
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

        self.ctrl_io_id = gobject.io_add_watch(
            self.ctrl_fd,
            gobject.IO_IN,
            self.ctrl_data_cb
        )

    def hello(self):
        print('------hello-------')
        os.write(self.ctrl_fd, '\xa1\x13\x03')
        os.write(self.ctrl_fd, '\xa1\x13\x02')

        time.sleep(1)

    def ctrl_data_cb(self, fd, io_type):
        data = os.read(fd, BUF_SIZE)

        handshake = HIDP_TRANS_HANDSHAKE
        msg_type = data[0] & HIDP_HEADER_TRANS_MASK

        if msg_type & HIDP_TRANS_SET_PROTOCOL:
            print('set protocol')
            handshake |= HIDP_HSHK_SUCCESSFUL
            os.write(fd, handshake)
            return True

        if msg_type & HIDP_TRANS_DATA:
            print('data')
            return True

        print('unknown error')
        handshake |= HIDP_HSHK_ERR_UNKNOWN
        os.write(fd, handshake)
        return True

    def register_intr_sock(self, sock):
        self.hello()
        self.intr_sock = sock
        keyboard.register_intr_sock(self.intr_sock)

    def close(self):
        pass

class HIDProfile(dbus.service.Object):
    conns = {}
    sock = None

    def __init__(self, bus, path, sock):
        dbus.service.Object.__init__(self, bus, path)
        if (sock):
            self.sock = sock

    @dbus.service.method("org.bluez.Profile1",
                         in_signature="", out_signature="")
    def Release(self):
        print("Release")
        mainloop.quit()

    @dbus.service.method("org.bluez.Profile1",
                         in_signature="o", out_signature="")
    def RequestDisconnection(self, path):
        print('RequestDisconnection')
        conns.pop(path).close()

    @dbus.service.method("org.bluez.Profile1",
                         in_signature="oha{sv}", out_signature="")
    def NewConnection(self, path, fd, properties):
        print("new control connectin")
        self.conns[path] = HIDConnection(fd.take())

        def new_intr_conn(ssock, ip_type):
            sock, info = ssock.accept()
            print("interrput connection:", info)
            self.conns[path].register_intr_sock(sock)

            return False

        gobject.io_add_watch(self.sock, gobject.IO_IN, new_intr_conn)


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    obj_path = '/ml/jlyu/HIDProfile'

    sock = bt.BluetoothSocket(bt.L2CAP)
    sock.setblocking(False)
    try:
        sock.bind(('', PSM_INTR))
    except:
        print("Someone has the bluetooth HID socket open, it might be bluetoothd")
        print("For bluez5 add --noplugin=input to the bluetoothd commandline")
        print("For bluez4 add PluginsDisable=input to /etc/bluetooth/main.conf")
        print("Else there is another application running that has it open.")
        sys.exit(errno.EACCES)
    sock.listen(1)

    profile = HIDProfile(bus, obj_path, sock)

    opts = {
        "PSM": dbus.UInt16(PSM_CTRL),
        "ServiceRecord": open('./sdp_record.xml', 'r').read(),
        "RequireAuthentication": dbus.Boolean(True),
        "RequireAuthorization": dbus.Boolean(False),
    }
    dbus.Interface(
        bus.get_object("org.bluez", "/org/bluez"),
        "org.bluez.ProfileManager1"
    ).RegisterProfile(obj_path, str(uuid.uuid4()), opts)

    gobject.MainLoop().run()


if __name__ == '__main__':
    main()
