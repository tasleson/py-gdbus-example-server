from gi.repository import Gio, GLib
import sys


# Attempted port of
# https://git.gnome.org/browse/glib/tree/gio/tests/gdbus-example-server.c
# using python bindings as an exercise to see if writing a dbus service with
# this approach is feasible.

# If you get the following error:
# AttributeError: type object 'DBusConnection' \
#     has no attribute 'register_object_with_closures
# Then you need to fetch the code and patch with:
# https://bug656325.bugzilla-attachments.gnome.org/attachment.cgi?id=288258

introspection_data = None
title = None
swap_a_and_b = False


def dump_args(func):
    """
    Using for debugging...
    """
    def wrapper(*func_args, **func_kwargs):
        arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
        args = func_args[:len(arg_names)]
        defaults = func.__defaults__ or ()
        args = args + defaults[len(defaults) -
                               (func.__code__.co_argcount - len(args)):]
        params = list(zip(arg_names, args))
        args = func_args[len(arg_names):]
        if args:
            params.append(('args', args))
        if func_kwargs:
            params.append(('kwargs', func_kwargs))
        print(func.__name__ +
              ' (' + ', '.join('%s = %r' % p for p in params) + ' )')
        return func(*func_args, **func_kwargs)
    return wrapper

# Introspection data for the service we are exporting
introspection_xml =  \
    '''
    <node>
        <interface name='org.gtk.GDBus.TestInterface'>
        <annotation name='org.gtk.GDBus.Annotation' value='OnInterface'/>
        <annotation name='org.gtk.GDBus.Annotation' value='AlsoOnInterface'/>
        <method name='HelloWorld'>
          <annotation name='org.gtk.GDBus.Annotation' value='OnMethod'/>
          <arg type='s' name='greeting' direction='in'/>
          <arg type='s' name='response' direction='out'/>
        </method>
        <method name='EmitSignal'>
          <arg type='d' name='speed_in_mph' direction='in'>
            <annotation name='org.gtk.GDBus.Annotation' value='OnArg'/>
          </arg>
        </method>
        <method name='GimmeStdout'/>
        <signal name='VelocityChanged'>
          <annotation name='org.gtk.GDBus.Annotation' value='Onsignal'/>
          <arg type='d' name='speed_in_mph'/>
          <arg type='s' name='speed_as_string'>
            <annotation name='org.gtk.GDBus.Annotation' value='OnArg_NonFirst'/>
          </arg>
        </signal>
        <property type='s' name='FluxCapicitorName' access='read'>
          <annotation name='org.gtk.GDBus.Annotation' value='OnProperty'>
            <annotation name='org.gtk.GDBus.Annotation' value='OnAnnotation_YesThisIsCrazy'/>
          </annotation>
        </property>
        <property type='s' name='Title' access='readwrite'/>
        <property type='s' name='ReadingAlwaysThrowsError' access='read'/>
        <property type='s' name='WritingAlwaysThrowsError' access='readwrite'/>
        <property type='s' name='OnlyWritable' access='write'/>
        <property type='s' name='Foo' access='read'/>
        <property type='s' name='Bar' access='read'/>
        </interface>
    </node>
    '''


def tt_value():
    """
    Returns a tuple for current values of (Foo, Bar)
    """
    t = ("Tick", "Tock")

    if swap_a_and_b:
        return t[::-1]
    else:
        return t


@dump_args
def handle_method_call(connection, sender, object_path, interface_name,
                       method_name, parameters, invocation):

    if method_name == "HelloWorld":
        greeting = parameters[0]

        if greeting == "Return Unregistered":
            # TODO is this the correct function?
            # self, domain:int, code:int, message:str)
            Gio.DBusMethodInvocation.return_error_literal(
                invocation,
                60,   # Where is G_IO_ERROR ?
                30,  # Where is G_IO_ERROR_FAILED_HANDLED ?
                "As requested, here's a GError not registered "
                "(G_IO_ERROR_FAILED_HANDLED)")
        elif greeting == "Return Registered":
            # TODO is this the correct function?
            # self, domain:int, code:int, message:str)
            Gio.DBusMethodInvocation.return_error_literal(
                invocation,
                60,   # Where is G_IO_ERROR ?
                21,  # Where is G_DBUS_ERROR_MATCH_RULE_NOT_FOUND ?
               "As requested, here's a GError that is registered "
               "(G_DBUS_ERROR_MATCH_RULE_NOT_FOUND)")
        elif greeting == "Return Raw":
            Gio.DBusMethodInvocation.return_dbus_error(
                invocation,
                "org.gtk.GDBus.SomeErrorName",
                "As requested, here's a raw D-Bus error")
        else:
            # TODO Can we construct this like the C version instead?
            ret = GLib.Variant("s", "You greeted me with '%s'. Thanks!" %
                               greeting)
            t = GLib.Variant.new_tuple(ret)
            invocation.return_value(t)
    elif method_name == "EmitSignal":
        speed_in_mph = long(parameters[0])
        speed_as_string = "%d mph!" % speed_in_mph

        # TODO Is there a better way to build these values?
        speed_double = GLib.Variant("d", speed_in_mph)
        speed_string = GLib.Variant("s", speed_as_string)
        values = GLib.Variant.new_tuple(speed_double, speed_string)

        Gio.DBusConnection.emit_signal(
            connection,
            None,
            object_path,
            interface_name,
            "VelocityChanged",
            values
        )
        invocation.return_value(None)
    elif method_name == "GimmeStdout":
        # TODO Add this...
        Gio.DBusMethodInvocation.return_dbus_error(
            invocation,
            "org.gtk.GDBus.Failed",
            "This part not implemented yet")

    return None


@dump_args
def handle_get_property(connection, sender, object_path, interface, value):
    global title
    global swap_a_and_b

    ret = None

    if value == 'FluxCapicitorName':
        ret = GLib.Variant("s", "DeLorean")
    elif value == 'Title':
        if title is None:
            title = "Back To C!"
        ret = GLib.Variant("s", title)
    elif value == 'ReadingAlwaysThrowsError':
        msg = "Hello %s. I thought I said reading this "" \
                ""property always results in an error. kthxbye" % sender
        # TODO This is not working, how should it be called or what should
        # we be calling? Where are the constants for:
        # G_IO_ERROR & G_IO_ERROR_FAILED
        #
        # We are getting...
        # TypeError: set_error_literal() takes exactly 3 arguments (4 given)
        # GLib.set_error_literal(None, 60, 0, msg)

    elif value == 'WritingAlwaysThrowsError':
        ret = GLib.Variant("s", "There's no home like home")
    elif value == "Foo":
        ret = GLib.Variant("s", tt_value()[0])
    elif value == "Bar":
        ret = GLib.Variant("s", tt_value()[1])

    return ret

@dump_args
def handle_set_property(connection, sender, object_path, interface_name, key,
                        value):
    global title

    if key == "Title":
        title = value.get_string()

        # TODO Please tell me there is a better way to do this?
        p1 = GLib.Variant('s', str(interface_name))
        p2 = GLib.Variant('a{sv}',
                          {'Title': GLib.Variant('v',
                                                 GLib.Variant('s', title))})
        p3 = GLib.Variant('as', ())
        values = GLib.Variant.new_tuple(p1, p2, p3)

        Gio.DBusConnection.emit_signal(
            connection,
            None,
            object_path,
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            values
        )

    elif key == "ReadingAlwaysThrowsError":
        pass
    elif key == "WritingAlwaysThrowsError":
        msg = "Hello AGAIN %s. I thought I said writing this property " \
              "always results in an error. kthxbye" % sender
        # TODO This is not working, how should it be called or what should
        # we be calling? Where are the constants for:
        # G_IO_ERROR & G_IO_ERROR_FAILED
        #
        # We are getting...
        # TypeError: set_error_literal() takes exactly 3 arguments (4 given)
        # GLib.set_error_literal(None, 60, 0, msg)

    # What is the correct thing to return here on success?  It appears that
    # we need to return something other than None or what would be evaluated
    # to False for this call back to be successful.
    return True


@dump_args
def on_timeout_cb(connection):
    global swap_a_and_b

    swap_a_and_b = not swap_a_and_b

    # TODO Better way?
    p1 = GLib.Variant('s', "org.gtk.GDBus.TestInterface")
    p2 = GLib.Variant('a{sv}',
                      {'Foo': GLib.Variant('v',
                                           GLib.Variant('s', tt_value()[0])),
                       'Bar': GLib.Variant('v',
                                           GLib.Variant('s', tt_value()[1]))})
    p3 = GLib.Variant('as', ())
    values = GLib.Variant.new_tuple(p1, p2, p3)

    Gio.DBusConnection.emit_signal(
        connection,
        None,
        "/org/gtk/GDBus/TestObject",
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        values
    )
    return True


@dump_args
def on_bus_acquired(connection, name, *args):
    reg_id = Gio.DBusConnection.register_object_with_closures(
        connection,
        "/org/gtk/GDBus/TestObject",
        introspection_data.interfaces[0],
        handle_method_call,
        handle_get_property,
        handle_set_property)

    if reg_id == 0:
        print('Error while registering object!')
        sys.exit(1)

    # swap value of properties Foo and Bar every two seconds
    GLib.timeout_add_seconds(2, on_timeout_cb, connection)


@dump_args
def on_name_acquired(connection, name, *args):
    pass


@dump_args
def on_name_lost(connection, name, *args):
    sys.exit(1)


if __name__ == '__main__':
    # We are lazy here - we don't want to manually provide
    # the introspection data structures - so we just build
    # them from XML.
    # Note: Do not call unref with the returned value even if it's
    # available, see: https://bugzilla.gnome.org/show_bug.cgi?id=741578
    introspection_data = Gio.DBusNodeInfo.new_for_xml(introspection_xml)

    owner_id = Gio.bus_own_name(Gio.BusType.SESSION,
                                "org.gtk.GDBus.TestServer",
                                Gio.BusNameOwnerFlags.NONE,
                                on_bus_acquired,
                                on_name_acquired,
                                on_name_lost
                                )
    try:
        GLib.MainLoop().run()
    except KeyboardInterrupt:
        pass

    Gio.bus_unown_name(owner_id)
    sys.exit(0)
