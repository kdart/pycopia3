#!/usr/bin/python
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
# License: LGPL

"""
Command Interface for interacting with controllers.

"""

from pycopia import CLI
from pycopia import IO
from pycopia import UI

class ConfiguratorShellCLI(CLI.GenericCLI):

    def _setup(self, obj, name):
        # Obtain host name directly from device.
        # this also asserts the configurator is working.
        self._obj = obj
        hostname = obj.hostname()
        self._environ["hostname"] = hostname
        self._environ["PS1"] = "Configurator(%%I%s%%N)> " % (hostname,)
        self._namespace = {"ctor":self._obj, "environ":self._environ}
        self._reset_scopes()

    def tail(self, argv):
        """tail <fname> [<filter>]
    tail a file, using the optional filter regular expression to filter lines."""
        fname = argv[1]
        if len(argv) > 2:
            filt = argv[2]
        else:
            filt = None
        s = self._obj
        s.tail(fname, filt)
        try:
            while 1:
                l = s.readline()
                self._print(l)
        except KeyboardInterrupt:
            s.interrupt()

    def exit(self, argv):
        """exit
    Exit from root if root. If not root, exit shell configurator."""
        if self._obj.is_root():
            self._obj.exit()
            return
        else:
            self._obj.exit()
            raise CommandQuit


class ConfiguratorTheme(UI.DefaultTheme):
    pass

def controller_cli(argv):
    """controller_cli [-s <script>] [-g] <device>

    Interact with a DUT configurator. If no device is specified use the testbed DUT.

    Options:
        -g Use paged output (like 'more')
        -s <script> Run a CLI script from the given file instead of entering
           interactive mode.

    """
    import os
    from pycopia import getopt
    from pycopia.QA import controller
    from pycopia.QA import config

    paged = False
    script = None

    try:
        optlist, longopts, args = getopt.getopt(argv[1:], "s:?g")
    except GetoptError:
            print((controller_cli.__doc__))
            return
    for opt, val in optlist:
        if opt == "-?":
            print((controller_cli.__doc__))
            return
        elif opt == "-g":
            paged = True
        elif opt == "-s":
            script = val

    if not args:
        print((controller_cli.__doc__))
        return

    if paged:
        from pycopia import tty
        io = tty.PagedIO()
    else:
        io = IO.ConsoleIO()

    # do runtime setup
    cf = config.get_config(initdict=longopts)
    cf.reportfile = "controller_cli"
    cf.logbasename = "controller_cli.log"
    cf.arguments = argv

    dev = cf.devices[args[0]]

    cont = controller.get_configurator(dev, logfile=cf.logfile)

    # construct the CLI
    theme = ConfiguratorTheme("Controller> ")
    ui = UI.UserInterface(io, cf, theme)
    cmd = CLI.get_generic_cmd(cont, ui, ConfiguratorShellCLI)
    cmd.device = dev # stash actual device for future reference
    parser = CLI.CommandParser(cmd, historyfile=os.path.expandvars("$HOME/.hist_controller"))

    if script:
        try:
            parser.parse(script)
        except KeyboardInterrupt:
            pass
    else:
        parser.interact()
    try:
        cont.close()
    except:
        pass


if __name__ == "__main__":
    import sys
    controller_cli(sys.argv)
