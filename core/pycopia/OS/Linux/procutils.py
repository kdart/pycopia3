#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2014- Keith Dart <keith@dartworks.biz>
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
Process utilities.

"""


import os

from pycopia.OS.exitstatus import ExitStatus

def run_as(pwent, umask=0o22):
    """Drop privileges to given user's password entry, and set up
    environment. Assumes the parent process has root privileges.
    """
    os.umask(umask)
    home = pwent.home
    try:
      os.chdir(home)
    except OSError:
      os.chdir("/")
    # drop privs to user
    os.setgroups(pwent.groups)
    os.setgid(pwent.gid)
    os.setegid(pwent.gid)
    os.setuid(pwent.uid)
    os.seteuid(pwent.uid)
    os.environ["HOME"] = home
    os.environ["USER"] = pwent.name
    os.environ["LOGNAME"] = pwent.name
    os.environ["SHELL"] = pwent.shell
    os.environ["PATH"] = "/bin:/usr/bin:/usr/local/bin"
    return None


def system(cmd):
    """Like os.system(), except returns ExitStatus object."""
    sts = os.system(cmd)
    return ExitStatus(sts, cmd)

