from gi.repository import GLib, Gio

class Server(object):
    def __init__(self, bus, path):
        self.loop = GLib.MainLoop()

        interface_info = Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces[0]

        method_outargs = {}
        method_inargs = {}
        for method in interface_info.methods:
            method_outargs[method.name] = '(' + ''.join([arg.signature for arg in method.out_args]) + ')'
            method_inargs[method.name] = tuple(arg.name for arg in method.in_args)

        self.method_inargs = method_inargs
        self.method_outargs = method_outargs

        bus.register_object(object_path=path, interface_info=interface_info, method_call_closure=self.on_method_call)

    def run(self):
        self.loop.run()

    def quit(self):
        self.loop.quit()

    def on_method_call(self,
                       connection,
                       sender,
                       object_path,
                       interface_name,
                       method_name,
                       parameters,
                       invocation):

        import IPython
        IPython.embed()
        kwargs = dict(zip(self.method_inargs[method_name], parameters.unpack()))
        result = getattr(self, method_name)(**kwargs)

        if type(result) is list:
            result = tuple(result)
        elif not type(result) is tuple:
            result = (result,)

        invocation.return_value(GLib.Variant(self.method_outargs[method_name], result))

class Foo(Server):
    '''
<node>
	<interface name='net.lvht.Foo1'>
		<method name='HelloWorld'>
			<arg type='s' name='a' direction='in'/>
			<arg type='i' name='b' direction='in'/>
			<arg type='s' name='c' direction='out'/>
			<arg type='s' name='d' direction='out'/>
		</method>
	</interface>
</node>
    '''
    def HelloWorld(self, a, b):
        return ('+' + a, '+{}'.format(b))


if __name__ == '__main__':
    from pydbus import SessionBus
    bus = SessionBus()
    bus.own_name(name = 'net.lvht')

    foo = Foo(bus=bus.con, path='/net/lvht/Foo')
    foo.run()
