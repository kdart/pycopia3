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
Name server control module. Slightly enhanced for QA package.
"""

from pycopia.remote import pyro


def print_listing(listing):
    for name, uri in sorted(listing.items()):
        if len(uri) > 45:
            print(("{:>35.35s} --> \n{:>79.79s}".format(name, uri)))
        else:
            print(("{:>35.35s} --> {}".format(name, uri)))


_DOC = """nsc [-h?]

Control or query the name server.

Subcommands:
    list - show current objects.
    ping - No error if server is reachable.
    remove <name> - remove the named agent entry.

"""

def nsc(argv):
    import getopt
    try:
        optlist, args = getopt.getopt(argv[1:], "h?")
    except getopt.GetoptError:
        print(_DOC)
        return 2

    for opt, optarg in optlist:
        if opt in ("-h", "-?"):
            print(_DOC)
            return

    try:
        subcmd = args[0]
    except IndexError:
        print(_DOC)
        return 2

    args = args[1:]
    nameserver = pyro.locate_nameserver()
    if subcmd.startswith("li"):
        if args:
            print_listing(nameserver.list(prefix=args[0]))
        else:
            print_listing(nameserver.list())
    elif subcmd.startswith("pi"):
        nameserver.ping()
        print("Name server is alive.")
    if subcmd.startswith("rem"):
        if args:
            nameserver.remove(name=args[0])
        else:
            print(_DOC)
            return 2


if __name__ == "__main__":
    import sys
    from pycopia import autodebug
    nsc(sys.argv)

