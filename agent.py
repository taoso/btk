from __future__ import print_function
#from future.builtins import input
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
import evdev as ev
import glob

from btk import HIDProfile, PSM_CTRL, PSM_INTR
import uuid
import bluetooth as bt

try:
    from gi.repository import GObject as gobject
except ImportError:
    import gobject


BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/test/agent"

def ask(prompt):
    return 1111 # input(prompt)

def set_trusted(path):
    props = dbus.Interface(bus.get_object("org.bluez", path),
                           "org.freedesktop.DBus.Properties")
    print('trust', path)
    props.Set("org.bluez.Device1", "Trusted", True)

def dev_connect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path),
                         "org.bluez.Device1")
    dev.Connect()

class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"

class Agent(dbus.service.Object):
    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="", out_signature="")
    def Release(self):
        print("Release")

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorize = ask("Authorize connection (yes/no): ")
        if (authorize == "yes"):
            return
        raise Rejected("Connection rejected by user")

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print("RequestPasskey (%s)" % (device))
        passkey = ""
        kb = ev.InputDevice(glob.glob('/dev/input/by-path/*event-kbd')[0])
        print(kb)
        for event in kb.read_loop():
            data = ev.categorize(event)
            if event.type != ev.ecodes.EV_KEY:
                continue
            elif data.keystate == 0: # ignore keyup
                continue

            key = ev.ecodes.KEY[event.code][4:]
            if key == 'ENTER': # we are done
                break
            elif key in ['1','2','3','4','5','6','7','8','9','0']:
                passkey = passkey + key

        set_trusted(device)
        return dbus.UInt32(passkey)

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print("DisplayPasskey (%s, %06u entered %u)" %
              (device, passkey, entered))

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print("DisplayPinCode (%s, %s)" % (device, pincode))

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = ask("Confirm passkey ([y]/n): ")
        if (confirm != "n"):
            set_trusted(device)
            return
        raise Rejected("Passkey doesn't match")

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? ([y]/n): ")
        if (auth != "n"):
            return
        raise Rejected("Pairing rejected")

    @dbus.service.method(AGENT_INTERFACE,
                         in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    props = dbus.Interface(
        bus.get_object("org.bluez", '/org/bluez/hci0'),
        "org.freedesktop.DBus.Properties"
    )
    props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))


    capability = "KeyboardOnly"
    path = "/test/agent"
    agent = Agent(bus, path)
    obj = bus.get_object('org.bluez', "/org/bluez");
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    manager.RegisterAgent(path, capability)
    manager.RequestDefaultAgent(path)

    print('start hid')
    sock = bt.BluetoothSocket(bt.L2CAP)
    sock.setblocking(False)
    sock.bind(('', PSM_INTR))
    sock.listen(1)

    obj_path = '/ml/jlyu/HIDProfile'
    profile = HIDProfile(bus, obj_path, sock)

    opts = {
        "PSM": dbus.UInt16(PSM_CTRL),
        "ServiceRecord": open('./sdp_record.xml', 'r').read(),
        "RequireAuthentication": dbus.Boolean(True),
        "RequireAuthorization": dbus.Boolean(True),
    }
    dbus.Interface(
        bus.get_object("org.bluez", "/org/bluez"),
        "org.bluez.ProfileManager1"
    ).RegisterProfile(obj_path, str(uuid.uuid4()), opts)

    gobject.MainLoop().run()

