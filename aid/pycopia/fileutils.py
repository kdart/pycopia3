#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 1999- Keith Dart <keith@kdart.com>
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.


"""

"""

import os
import fcntl


class MergedIO(object):
    """MergedIO(outfile, infile)
Combines a write stream and a read stream into one read/write object."""
    def __init__(self, outf, inf):
        self._outf = outf
        self._inf = inf
        self.mode = "rw"
        self.closed = 0
        self.softspace = 0
        # reading methods
        self.read = inf.read
        self.readline = inf.readline
        self.readlines = inf.readlines
        # writing methods
        self.write = outf.write
        self.flush = outf.flush
        self.writelines = outf.writelines

    def close(self):
        self._outf.close()
        self._inf.close()
        self._outf = None
        self._inf = None
        self.closed = 1

    def fileno(self): # ??? punt, since reads are most common, return reader fd
        return self._inf.fileno()

    def filenos(self):
        return self._inf.fileno(), self._outf.fileno()

    def isatty(self):
        return self._inf.isatty() and self._outf.isatty()



def mode2flags(mode):
    """mode2flags(modestring)
    Converts a file mode in string form (e.g. "w+") to an integer flag value
    suitable for os.open().  """
    flags = os.O_LARGEFILE # XXX only when Python compiled with large file support
    if mode == "a":
        flags = flags | os.O_APPEND | os.O_WRONLY
    elif mode == "a+":
        flags = flags | os.O_APPEND | os.O_RDWR | os.O_CREAT
    elif mode == "w":
        flags = flags | os.O_WRONLY | os.O_CREAT
    elif mode == "w+":
        flags = flags | os.O_RDWR | os.O_CREAT
    elif mode == "r":
        pass # O_RDONLY is zero already
    elif mode == "r+":
        flags = flags | os.O_RDWR
    return flags


# cache of O_ flags
_OLIST = [n for n in dir(os) if n.startswith("O_")]

def flag_string(fd):
    """flag_string(fd)
    where fd is an integer file descriptor of an open file. Returns the files open
    flags as a vertical bar (|) delimited string.
    """
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    strlist = [_f for _f in [(flags & getattr(os, n)) and n for n in _OLIST] if _f]
    # hack to accomodate the fact that O_RDONLY is not really a flag...
    if not (flags & os.ACCMODE):
        strlist.insert(0, "O_RDONLY")
    return "|".join(strlist)


# TODO still need to verify this or add more.
_MODEMAP = {
    os.O_RDONLY: "r",
    os.O_RDWR: "r+",
    os.O_WRONLY | os.O_TRUNC: "w",
    os.O_RDWR | os.O_CREAT: "w+",
    os.O_APPEND | os.O_WRONLY: "a",
    os.O_APPEND | os.O_RDWR | os.O_CREAT: "a+",
}

def mode_string(fd):
    """Get a suitalbe mode string for an fd."""
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    mode = _MODEMAP.get(flags)
    if mode is None:
        return flag_string(fd)
    else:
        return mode


def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def set_nonblocking(fd, flag=1):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    if flag:
        flags |= os.O_NONBLOCK # set non-blocking
    else:
        flags &= ~os.O_NONBLOCK # set blocking
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)

