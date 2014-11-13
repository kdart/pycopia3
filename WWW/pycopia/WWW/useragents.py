#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 1999-2006  Keith Dart <keith@kdart.com>
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
A collection of Web browser user agent strings.
Culled from actual apache log file.

"""

import os


def get_useragents():
    """Return a list of possible user-agent keywords."""
    rv = []
    fname = os.path.join(os.path.dirname(__file__), "useragents.txt")
    with open(fname) as fo:
        for line in fo:
            try:
                name, agentstring = line.split("|", 1)
            except ValueError:
                continue
            rv.append(name)
    return sorted(rv)


def get_useragent(name):
    """Select a user agent from the data file."""
    fname = os.path.join(os.path.dirname(__file__), "useragents.txt")
    with open(fname) as fo:
        for line in fo:
            try:
                agentname, agentstring = line.split("|", 1)
            except ValueError:
                continue
            if name == agentname.strip():
                return agentstring.strip()

