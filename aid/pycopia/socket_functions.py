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
Utility functions for opening client and server sockets.
"""

import struct
import fcntl
from errno import EADDRNOTAVAIL
from socket import (socket, getaddrinfo, gethostbyname, getfqdn,
                    IPPORT_USERRESERVED, SOL_SOCKET, SO_REUSEADDR,
                    AF_INET, AF_UNIX, SOCK_DGRAM, SOCK_STREAM)

# Extra ioctl numbers, for Linux
SIOCINQ = 0x541B
SIOCOUTQ = 0x5411

# client connections

def connect_inet(host, port, socktype, sobject=socket):
    """General client connections."""
    args = getaddrinfo(str(host), int(port), AF_INET, socktype)
    for family, socktype, proto, canonname, sockaddr in args:
        try:
            s = sobject(family, socktype, proto)
            s.connect(sockaddr)
        except:
            continue
        else:
            return s
    raise OSError("Could not connect to {}:{}".format(host, port))


def connect_tcp(host, port, sobject=socket):
    """Make a TCP client connection."""
    return connect_inet(host, port, SOCK_STREAM, sobject)


def connect_udp(host, port, sobject=socket):
    """Make a UDP client connection."""
    return connect_inet(host, port, SOCK_DGRAM, sobject)


def connect_unix(path, sobject=socket):
    """Make a Unix socket stream client connection."""
    s = sobject(AF_UNIX, SOCK_STREAM)
    s.connect(path)
    return s


def connect_unix_datagram(path, sobject=socket):
    s = sobject(AF_UNIX, SOCK_DGRAM)
    s.connect(path)
    return s


# server (listener) maker functions:

def unix_listener(path, num=5, sobject=socket):
    try:
        os.unlink(path)
    except:
        pass
    s = sobject(AF_UNIX, SOCK_STREAM)
    s.bind(path)
    s.listen(num)
    return s


def unix_listener_datagram(path, num=5, sobject=socket):
    s = sobject(AF_UNIX, SOCK_DGRAM)
    s.bind(path)
    return s


def udp_listener(addr, num=5, sobject=socket):
    """return a bound UDP socket."""
    s = sobject(AF_INET, SOCK_DGRAM)
    s.bind(addr)
    return s


def tcp_listener(addr, num=5, sobject=socket):
    """return a TCP socket, bound and listening."""
    s = sobject(AF_INET, SOCK_STREAM)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(num)
    return s


# utility functions:

def check_port(host, port):
    """Checks a TCP port on a remote host for a listener. Returns true if a
    connection is possible, false otherwise."""
    try:
        s = connect_tcp(host, port)
    except OSError:
        return 0
    s.close()
    return 1


def islocal(host):
    """islocal(host) tests if the given host is ourself, or not."""
    # try to bind to the address, if successful it is local...
    ip = gethostbyname(getfqdn(host))
    s = socket(AF_INET, SOCK_STREAM)
    try:
        s.bind((ip, IPPORT_USERRESERVED+1))
    except OSError as err:
        if err.errno == EADDRNOTAVAIL:
            return 0
        else:
            raise
    else:
        s.close()
        return 1


def inq(sock):
    """How many bytes are still in the kernel's input buffer?"""
    return struct.unpack("I",
                         fcntl.ioctl(sock.fileno(), SIOCINQ, '\0\0\0\0'))[0]


def outq(sock):
    """How many bytes are still in the kernel's output buffer?"""
    return struct.unpack("I",
                         fcntl.ioctl(sock.fileno(), SIOCOUTQ, '\0\0\0\0'))[0]
