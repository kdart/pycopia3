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

