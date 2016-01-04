from __future__ import print_function

import sys
import evdev as ev
import glob

from btk import HIDProfile, PSM_CTRL, PSM_INTR
import uuid
import bluetooth as bt

from gi.repository import GLib

from pydbus import SystemBus
from dbus import Server

bus = SystemBus()

def ask(prompt):
    return 1111 # input(prompt)

def set_trusted(path):
    props = bus.get('org.bluez', path)['org.freedesktop.DBus.Properties']
    print('trust', path)
    props.Set("org.bluez.Device1", "Trusted", GLib.Variant.new_boolean(True))

def dev_connect(path):
    dev = bus.get('org.bluez', path)['org.bluez.Device1']
    dev.Connect()


class Agent(Server):
    '''
<node>
	<interface name='org.bluez.Agent1'>
		<method name='Release'></method>
		<method name='AuthorizeService'>
			<arg type='o' name='device' direction='in'/>
			<arg type='s' name='uuid' direction='in'/>
		</method>
		<method name='RequestPinCode'>
			<arg type='o' name='device' direction='in'/>
			<arg type='s' name='pin_code' direction='out'/>
		</method>
		<method name='RequestPasskey'>
			<arg type='o' name='device' direction='in'/>
			<arg type='u' name='pass_key' direction='out'/>
		</method>
		<method name='DisplayPasskey'>
			<arg type='o' name='device' direction='in'/>
			<arg type='u' name='pass_key' direction='in'/>
			<arg type='q' name='entered' direction='in'/>
		</method>
		<method name='DisplayPinCode'>
			<arg type='o' name='device' direction='in'/>
			<arg type='s' name='pin_code' direction='in'/>
		</method>
		<method name='RequestConfirmation'>
			<arg type='o' name='device' direction='in'/>
			<arg type='s' name='pass_key' direction='in'/>
		</method>
		<method name='RequestAuthorization'>
			<arg type='o' name='device' direction='in'/>
		</method>
        <method name='Cancel'></method>
	</interface>
</node>
    '''
    def Release(self):
        print("Release")

    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorize = ask("Authorize connection (yes/no): ")
        if (authorize == "yes"):
            return

    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

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
        return int(passkey)

    def DisplayPasskey(self, device, passkey, entered):
        print("DisplayPasskey (%s, %06u entered %u)" %
              (device, passkey, entered))

    def DisplayPinCode(self, device, pincode):
        print("DisplayPinCode (%s, %s)" % (device, pincode))

    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = ask("Confirm passkey ([y]/n): ")

    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? ([y]/n): ")

    def Cancel(self):
        print("Cancel")

if __name__ == '__main__':
    props = bus.get('org.bluez', '/org/bluez/hci0')['org.freedesktop.DBus.Properties']
    props.Set("org.bluez.Adapter1", "Powered", GLib.Variant.new_boolean(True))
    props.Set("org.bluez.Adapter1", "Discoverable", GLib.Variant.new_boolean(True))

    capability = "KeyboardOnly"
    path = "/net/lvht/btk/agent"
    agent = Agent(bus.con, path)
    manager = bus.get('org.bluez')['.AgentManager1']
    manager.RegisterAgent(path, capability)
    manager.RequestDefaultAgent(path)

    print('start hid')
    sock = bt.BluetoothSocket(bt.L2CAP)
    sock.setblocking(False)
    sock.bind(('', PSM_INTR))
    sock.listen(1)

    obj_path = '/net/lvht/btk/HIDProfile'
    profile = HIDProfile(bus.con, obj_path, sock)

    opts = {
        "PSM": GLib.Variant.new_uint16(PSM_CTRL),
        "ServiceRecord": GLib.Variant.new_string(open('./sdp_record.xml', 'r').read()),
        "RequireAuthentication": GLib.Variant.new_boolean(True),
        "RequireAuthorization": GLib.Variant.new_boolean(True),
    }
    manager = bus.get('org.bluez')['.ProfileManager1']
    manager.RegisterProfile(obj_path, str(uuid.uuid4()), opts)

    GLib.MainLoop().run()
