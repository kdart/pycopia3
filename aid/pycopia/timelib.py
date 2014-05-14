#!/usr/bin/python
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) Keith Dart <keith@kdart.com>
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
Extra time related functions.

"""

from time import *
now = time

# Python time tuple:
# Index   Attribute   Values
# 0 tm_year (for example, 1993)
# 1 tm_mon range [1,12]
# 2 tm_mday range [1,31]
# 3 tm_hour range [0,23]
# 4 tm_min range [0,59]
# 5 tm_sec range [0,61]; see (1) in strftime() description
# 6 tm_wday range [0,6], Monday is 0
# 7 tm_yday range [1,366]
# 8 tm_isdst 0, 1 or -1; see below


def seconds(seconds=0, minutes=0, hours=0, days=0, weeks=0):
    """Returns a value in seconds given some minutes, hours, days, or weeks."""
    return seconds + minutes*60 + hours*3600 + days*86400 + weeks*604800

def HMS(secs):
    """Return tuple of hours, minutes, and seconds given value in seconds."""
    minutes, seconds = divmod(secs, 60.0)
    hours, minutes = divmod(minutes, 60.0)
    return hours, minutes, seconds

def HMS2str(hours, minutes, seconds):
    return "%02.0f:%02.0f:%02.2f" % (hours, minutes, seconds)

def gmtimestamp(fmt="%a, %d %b %Y %H:%M:%S +0000", tm=None):
    return strftime(fmt, tm or gmtime())
rfc822time = gmtimestamp

def timestamp(secs=None, fmt="%a, %d %b %Y %H:%M:%S +0000"):
    """Return string with current time, according to given format. Default is
rfc822 compliant date value."""
    if secs:
        return strftime(fmt, gmtime(secs))
    else:
        return strftime(fmt, gmtime())

def localtimestamp(secs=None, fmt="%a, %d %b %Y %H:%M:%S %Z"):
    """Return string with , according to given format. Default is
rfc822 compliant date value."""
    if secs:
        return strftime(fmt, localtime(secs))
    else:
        return strftime(fmt, localtime())

def strptime_localtimestamp(ts, fmt="%a, %d %b %Y %H:%M:%S %Z"):
    """Return seconds given a local timestamp string (inverse of
    localtimestamp function).
    """
    return mktime(strptime(ts, fmt))

