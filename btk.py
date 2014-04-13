import dbus
import dbus.mainloop.glib
import dbus.service
import gobject
import os
import uuid

mainloop = None
BUF_SIZE = 1024

class HIDConnection:
    io_id = None
    fd = -1
    def __init__(self, fd):
        self.fd = fd.take()
        self.io_id = gobject.io_add_watch(self.fd, gobject.IO_IN, self.data_cb)

    def data_cb(self, fd, cond):
        data = os.read(fd, BUF_SIZE)
        print("received", data)
        return True

    def close(self):
        print("close connection")
        if self.io_id:
            gobject.source_remove(self.io_id)

        if (self.fd >= 0):
            os.close(fd)

class HIDProfile(dbus.service.Object):
    conns = {}

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
        print("NewConnection", path, fd)
        self.conns[path] = HIDConnection(fd)


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    obj_path = '/ml/jlyu/hid'
    profile = HIDProfile(bus, obj_path)

    opts = {
        "PSM": dbus.UInt16(0x37),
        "ServiceRecord": open('./sdp_record.xml', 'r').read()
    }
    dbus.Interface(
        bus.get_object("org.bluez", "/org/bluez"),
        "org.bluez.ProfileManager1"
    ).RegisterProfile(obj_path, str(uuid.uuid4()), opts)

    gobject.MainLoop().run()
