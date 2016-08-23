#!/usr/bin/python3
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Some functions helpful in Python's interactive mode.
The intent is to provide a little nicer REPL experience without requiring any
non-stock packages.  However, the jedi or rlcompleter2 packages will be used if
installed.
"""

import os
import sys
import importlib
from pprint import pprint

try:
    import readline
except ImportError:
    # dummy readline to make rest of this module happy in case readline is not
    # available.
    class Readline(object):
        def parse_and_bind(self, *args):
            pass

        def read_history_file(self, arg):
            pass

        def write_history_file(self, arg):
            pass
    readline = Readline()


_default_hist = os.path.join(os.environ["HOME"], ".python3hist")
PYHISTFILE = os.environ.get("PYHISTFILE", _default_hist)
del _default_hist


def savehist():
    readline.write_history_file(PYHISTFILE)

# Prefer jedi, if installed, then rlcompleter2, then built-in rlcompleter.
try:
    from jedi.utils import setup_readline
    import atexit
    setup_readline()
    try:
        readline.read_history_file(PYHISTFILE)
    except IOError:
        pass
    atexit.register(savehist)
except ImportError:
    try:
        import rlcompleter2
        rlcompleter2.setup(PYHISTFILE, verbose=0)
    except ImportError:
        import rlcompleter  # noqa
        import atexit
        try:
            readline.read_history_file(PYHISTFILE)
        except IOError:
            pass
        atexit.register(savehist)
    # readline key bindings
    if sys.platform == "darwin":
        readline.parse_and_bind("^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind('"\M-?": possible-completions')


# Insert some pycopia functions that are useful for interactive use.
tumod = importlib.import_module("pycopia.textutils")
mainmod = sys.modules["__main__"]
for _name in tumod.__all__:
    setattr(mainmod, _name, getattr(tumod, _name))
del tumod, mainmod, _name

sys.ps1 = os.environ.get("PYPS1", "Python{0}> ".format(sys.version_info[0]))
sys.ps2 = os.environ.get("PYPS2", "more...> ")


def mydisplayhook(obj):
    if obj is not None:
        pprint(obj)
        setattr(sys.modules["__main__"], "_", obj)

sys.displayhook = mydisplayhook
setattr(sys.modules["__main__"], "_", None)


# Other possible readline configuration.
# readline.parse_and_bind("tab: menu-complete")
# readline.parse_and_bind('"?": possible-completions')
# readline.parse_and_bind('"\M-h": "help()\n"')
# readline.parse_and_bind('"\eOP": "help()\n"')
# readline.parse_and_bind('"\M-f": dump-functions')
# readline.parse_and_bind('"\M-v": dump-variables')
# readline.parse_and_bind('"\M-m": dump-macros')
# readline.parse_and_bind("set editing-mode vi")
# readline.parse_and_bind("set show-all-if-ambiguous on")
# readline.parse_and_bind("set meta-flag on")
# readline.parse_and_bind("set input-meta on")
# readline.parse_and_bind("set output-meta on")
# readline.parse_and_bind("set convert-meta off")
