#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
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
Run things as root (or another user) via sudo.

"""
from pycopia import proctools
from pycopia.OS import procutils

SUDO = procutils.which("sudo")

def sudo(command, user=None, password=None, extraopts=None, logfile=None):
    opts = "-S %s" % ("-u %s" % user if user else "")
    cmd = "%s %s %s %s" % (SUDO, opts, extraopts or "", command)
    proc = proctools.spawnpipe(cmd, logfile=logfile, merge=0)
    if password:
        proc.readerr(9) # discard password prompt
        proc.write("%s\r" % (password,))
        proc.readerr(1) # discard newline
    return proc

def sudo_reset():
    proc = proctools.spawnpipe("%s -k" % (SUDO,), merge=0)
    proc.read()
    proc.wait()

def sudo_command(cmd, password=None, logfile=None):
    """Run a command with sudo and return the output."""
    proc = sudo(cmd, password, logfile=logfile)
    rv = proc.read()
    errs = proc.readerr()
    es = proc.wait()
    if errs or not es:
        raise RuntimeError((es, errs))
    return rv

def getpw():
    import getpass
    pw = getpass.getpass("sudo password: ")
    if not pw:
        return None
    return pw

