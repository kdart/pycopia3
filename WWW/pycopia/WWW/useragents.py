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


def get_useragent(name, default=None):
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
    return default

