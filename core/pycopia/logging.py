#!/usr/bin/python3.4
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
Replacement logging module. The Java-inspired Python logging module does not
follow best practices, and has a lot of unnecessary bloat.  Pycopia just lets
syslog handle everything, since it is usually run on systems with syslog-ng and
that can handle every feature you could want for logging.

The configuration file /etc/pycopia/logging.conf can set the default
logging parameters.
"""

import sys
import syslog


# stderr functions
def warn(*args):
    print(*args, file=sys.stderr)


def DEBUG(*args, **kwargs):
    """Can use this instead of 'print' when debugging. Prints to stderr.
    """
    parts = []
    for name, value in list(kwargs.items()):
        parts.append("{}: {!r}".format(name, value))
    print("DEBUG", " ".join(str(o) for o in args), ", ".join(parts),
          file=sys.stderr)

# config file is optional here
from pycopia import basicconfig
try:
    cf = basicconfig.get_config("logging.conf")
except basicconfig.ConfigReadError as err:
    warn(err, "Using default values.")
    FACILITY = "USER"
    LEVEL = "WARNING"
    USESTDERR = True
else:
    FACILITY = cf.FACILITY
    LEVEL = cf.LEVEL
    USESTDERR = cf.get("USESTDERR", True)
    del cf
del basicconfig


_oldloglevel = syslog.setlogmask(syslog.LOG_UPTO(
    getattr(syslog, "LOG_" + LEVEL)))


def openlog(ident=None, usestderr=USESTDERR, facility=FACILITY):
    opts = syslog.LOG_PID | syslog.LOG_PERROR if usestderr else syslog.LOG_PID
    if isinstance(facility, str):
        facility = getattr(syslog, "LOG_" + facility)
    if ident is None:  # alas, openlog does not take None as an ident parameter.
        syslog.openlog(logoption=opts, facility=facility)
    else:
        syslog.openlog(ident=ident, logoption=opts, facility=facility)

# Assume user wants to log already, according to the configuration.
openlog()


def close():
    syslog.closelog()


def debug(msg):
    syslog.syslog(syslog.LOG_DEBUG, _encode(msg))


def info(msg):
    syslog.syslog(syslog.LOG_INFO, _encode(msg))


def notice(msg):
    syslog.syslog(syslog.LOG_NOTICE, _encode(msg))


def warning(msg):
    syslog.syslog(syslog.LOG_WARNING, _encode(msg))


def error(msg):
    syslog.syslog(syslog.LOG_ERR, _encode(msg))


def critical(msg):
    syslog.syslog(syslog.LOG_CRIT, _encode(msg))


def alert(msg):
    syslog.syslog(syslog.LOG_ALERT, _encode(msg))


def emergency(msg):
    syslog.syslog(syslog.LOG_EMERG, _encode(msg))


# set loglevels
def get_logmask():
    return syslog.setlogmask(0)


def loglevel(level):
    global _oldloglevel
    _oldloglevel = syslog.setlogmask(syslog.LOG_UPTO(level))


def get_loglevel():
    mask = syslog.setlogmask(0)
    for level in (syslog.LOG_DEBUG, syslog.LOG_INFO, syslog.LOG_NOTICE,
                  syslog.LOG_WARNING, syslog.LOG_ERR, syslog.LOG_CRIT,
                  syslog.LOG_ALERT, syslog.LOG_EMERG):
        if syslog.LOG_MASK(level) & mask:
            return level


def loglevel_restore():
    syslog.setlogmask(_oldloglevel)


def loglevel_debug():
    loglevel(syslog.LOG_DEBUG)


def loglevel_info():
    loglevel(syslog.LOG_INFO)


def loglevel_notice():
    loglevel(syslog.LOG_NOTICE)


def loglevel_warning():
    loglevel(syslog.LOG_WARNING)


def loglevel_error():
    loglevel(syslog.LOG_ERR)


def loglevel_critical():
    loglevel(syslog.LOG_CRIT)


def loglevel_alert():
    loglevel(syslog.LOG_ALERT)


# common logging patterns
def exception_error(prefix):
    ex, val, tb = sys.exc_info()
    error("{}: {}: {}".format(prefix, ex.__name__, val))


def exception_warning(prefix):
    ex, val, tb = sys.exc_info()
    warning("{}: {}: {}".format(prefix, ex.__name__, val))


# compatibility functions
def msg(source, *msg):
    info("{0!s}: {1}".format(source, " ".join(str(o) for o in msg)))


def _encode(s):
    return s.replace("\r\n", " ")


# Allow use of names, and useful aliases, to select logging level.
LEVELS = {
    "DEBUG": syslog.LOG_DEBUG,
    "INFO": syslog.LOG_INFO,
    "NOTICE": syslog.LOG_NOTICE,
    "WARNING": syslog.LOG_WARNING,
    "WARN": syslog.LOG_WARNING,
    "ERR": syslog.LOG_ERR,
    "ERROR": syslog.LOG_ERR,
    "CRIT": syslog.LOG_CRIT,
    "CRITICAL": syslog.LOG_CRIT,
    "ALERT": syslog.LOG_ALERT,
}
LEVELS_REV = dict((v, k) for k, v in LEVELS.items())


class Logger:
    """Simple logger using only syslog."""
    def __init__(self, name=None, usestderr=False, facility=FACILITY):
        self.name = name or sys.argv[0].split("/")[-1]
        syslog.closelog()
        openlog(name, usestderr, facility)

    def __del__(self):
        self.close()

    def close(self):
        syslog.closelog()

    def debug(self, msg):
        debug(msg)

    def info(self, msg):
        info(msg)
    log = info

    def notice(self, msg):
        notice(msg)

    def warning(self, msg):
        warning(msg)

    def error(self, msg, exc_info=None):
        if exc_info is not None:
            ex, val, tb = exc_info
            tb = None  # noqa
            msg = "{}: {} ({})".format(msg, ex.__name__, val)
        error(msg)

    def critical(self, msg):
        critical(msg)

    def fatal(self, msg):
        critical(msg)

    def alert(self, msg):
        alert(msg)

    def emergency(self, msg):
        emergency(msg)

    def exception(self, ex, val, tb=None):
        error("Exception: {}: {}".format(ex.__name__, val))

    @property
    def logmask(self):
        return syslog.setlogmask(0)

    @logmask.setter
    def logmask(self, newmask):
        syslog.setlogmask(newmask)

    @property
    def loglevel(self):
        level = get_loglevel()
        return LEVELS_REV[level]

    @loglevel.setter
    def loglevel(self, newlevel):
        newlevel = LEVELS[newlevel.upper()]
        loglevel(newlevel)

    # compatibility methods, note the non-PEP8 names.
    def getEffectiveLevel(self):
        return get_loglevel()

    def setLevel(self, newlevel):
        loglevel(newlevel)  # TODO might need to translate level numbers.


class LogLevel:
    """Context manager to run a block of code at a specific log level.

    Supply the level name as a string.
    """
    def __init__(self, level):
        self._level = LEVELS[level.upper()]

    def __enter__(self):
        self._oldloglevel = syslog.setlogmask(syslog.LOG_UPTO(self._level))

    def __exit__(self, extype, exvalue, traceback):
        syslog.setlogmask(self._oldloglevel)
