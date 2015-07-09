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
An SCGI to WSGI gateway.
"""

import sys
import os
import socket
import signal
import syslog
import selectors

from pycopia.OS.procutils import run_as
from pycopia import netstring


class Logger:
    """File-like object for logging."""

    def __init__(self, name, facility):
        syslog.openlog(name, syslog.LOG_PID,
                       getattr(syslog, "LOG_" + facility))

    def flush(self):
        pass  # noop

    def write(self, msg):
        syslog.syslog(syslog.LOG_ERR, msg.replace("\r\n", " "))
        return len(msg)

    def writelines(self, seq):
        for s in seq:
            self.write(s)


class SCGIServer:

    def __init__(self, application, socketpath, pwent=None,
                 umask=None, debug=False):
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        self._app = application
        self._umask = umask
        self._path = socketpath
        self._sock = None
        self._pwent = pwent

    def __del__(self):
        self.close()

    def open(self):
        if self._sock is None:
            socketpath = self._path
            if os.path.exists(socketpath):
                os.unlink(socketpath)
            if self._umask is not None:
                original_umask = os.umask(self._umask)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(False)
            sock.bind(socketpath)
            sock.listen(50)
            if self._umask is not None:
                os.umask(original_umask)
            self._sock = sock
        return self._sock

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def run(self):
        reactor = selectors.DefaultSelector()
        sock = self.open()
        reactor.register(sock, selectors.EVENT_READ)
        while True:
            events = reactor.select()
            for key, mask in events:
                conn, addr = key.fileobj.accept()
                conn.set_inheritable(True)
                pid = os.fork()
                if pid == 0:
                    try:
                        if self._pwent is not None:
                            run_as(self._pwent)
                        _handle_request(self._app, conn)
                    finally:
                        conn.close()
                    os._exit(0)
                else:
                    conn.close()


CRLF = b"\r\n"

DEFAULT_ENVIRON = {
    'wsgi.version': (1,0),
    'wsgi.multithread': False,
    'wsgi.multiprocess': True,
    'wsgi.run_once': True,
}


def _handle_request(app, conn):
    env = DEFAULT_ENVIRON.copy()
    rawheaders = netstring.decode_stream(conn)
    it = iter(rawheaders.split(b"\0"))
    for key in it:
        if not key:
            break
        value = next(it)
        env[key.decode("latin1")] = value.decode("latin1")
    env['CONTENT_LENGTH'] = int(env["CONTENT_LENGTH"])
    env['wsgi.input'] = conn.makefile("rb", 32758)
    env['wsgi.errors'] = Logger(env["SCRIPT_NAME"], "LOCAL7")
    if env.get('HTTPS', 'off') in ('on', '1'):
        env['wsgi.url_scheme'] = 'https'
    else:
        env['wsgi.url_scheme'] = 'http'

    def start_response(status, headers, exc_info=None):
        if exc_info is not None:
            try:
                raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
            finally:
                exc_info = None
        conn.sendall("Status: {}\r\n".format(status).encode("ascii"))
        for h, v in headers:
            conn.sendall("{}: {}\r\n".format(h, v).encode("ascii"))
        conn.sendall(CRLF)

    if env["REQUEST_METHOD"] == "HEAD":
        app(env, start_response)
    else:
        for chunk in app(env, start_response):
            conn.sendall(chunk)  # app encodes the return
    env['wsgi.input'].close()

def test_app(env, start_response):
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [str(env).encode("utf-8")]


def _test(argv):
    srv = SCGIServer(test_app, "/tmp/testscgi.sock")
    try:
        srv.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    from pycopia import autodebug
    import sys
    _test(sys.argv)

