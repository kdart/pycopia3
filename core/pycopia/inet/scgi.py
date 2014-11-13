#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2012- Keith Dart <keith@dartworks.biz>
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
An SCGI to WSGI gateway.
"""

import os
import socket
import selectors

from pycopia import netstring


class SCGIServer:

    def __init__(self, application, socketpath, environ=None, bind=None, umask=None, debug=False):
        self._app = application
        self._path = socketpath
        self._sock = None

    def open(self):
        if self._sock is None:
            socketpath = self._path
            if os.path.exists(socketpath):
                os.unlink(socketpath)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(False)
            sock.bind(socketpath)
            sock.listen(50)
            self._sock = sock
        return self._sock

    def run(self):
        reactor = selectors.DefaultSelector()
        sock = self.open()
        reactor.register(sock, selectors.EVENT_READ, self._accept)

        while True:
            events = reactor.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)


        new_s, addr = sock.accept()
        new_s.setblocking(False)
        rawreq = netstring.decode_stream(new_s)
        print(repr(rawreq))

        new_s.close()

    def _accept(self):
        conn, addr = self._sock.accept()


#####################3

sel = selectors.DefaultSelector()

def accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    print('accepted', conn, 'from', addr)
    sel.register(conn, selectors.EVENT_READ, read)

def read(conn, mask):
    data = conn.recv(1000)  # Should be ready
    if data:
        print('echoing', repr(data), 'to', conn)
        conn.send(data)  # Hope it won't block
    else:
        print('closing', conn)
        sel.unregister(conn)
        conn.close()



sock = socket.socket()
sock.bind(('localhost', 1234))
sock.listen(100)
sel.register(sock, selectors.EVENT_READ, accept)

while True:
    events = sel.select()
    for key, mask in events:
        callback = key.data
        callback(key.fileobj, mask)



def _test(argv):

    pass

if __name__ == "__main__":
    import sys
    _test(sys.argv)

