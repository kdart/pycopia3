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
This module contains classes and functions that perform Expect-like operations
on file objects. It is a general and object oriented approach to interacting
with files and processes. Use this in concert with the proctools module for
interacting with processes.
"""

import os
import re
import fnmatch
from errno import EINTR

from pycopia import scheduler
from pycopia.stringmatch import compile_exact
import collections

# matching types
EXACT = 1  # string match (fastest)
GLOB = 2   # POSIX shell style match, but really uses regular expressions
REGEX = 3  # slow but powerful RE match


class ExpectError(Exception):
    """Raised when the unexpected happens."""
    pass


class Expect:
    """Expect wraps a file-like object and provides enhanced read, write,
readline, send, and expect methods. This is very useful when combined with
proctool objects running interactive programs (A Process object is a
file-like object as well).

The wrapped object need only implement the following methods:

    Mandatory:
        read(n)
        write(s)
        close()
        fileno()

    Optional:
        restart(bool) - Turn on or off system call restart.
        dup()         - Duplicate the object and file descriptor (for cloning)
        interrupt()   - Interrupt the wrapped object (usually a process object)

"""
    def __init__(self, fo=None, prompt="$", timeout=90.0, logfile=None,
                 engine=None):
        if hasattr(fo, "fileno"):
            self._fo = fo
            try:
                # for Process objects. This needs to catch EINTR for timeouts.
                self._fo.restart(0)
            except AttributeError:
                pass
        else:
            raise ValueError("Expect: first parameter not a file-like object.")
        self.default_timeout = timeout
        self._log = logfile
        self.cmd_interp = None
        self._prompt = prompt.encode()
        self._patt_cache = {}
        self._buf = ''
        self.eof = 0
        self.sched = scheduler.get_scheduler()
        self._engine = engine
        # If a match on a list occurs, the index in the list
        # search on the last 'expect' method call is saved here.
        self.expectindex = -1

    def fileobject(self):
        return self._fo

    def fileno(self):
        return self._fo.fileno()

    def openlog(self, fname):
        try:
            self._log = open(fname, "w")
        except:
            self._log = None
            raise

    def close(self):
        if self._fo:
            fo = self._fo
            self._fo = None
            try:
                # for Process objects, back to syscall restart mode if we are
                # no longer wrapping it.
                fo.restart(1)
            except AttributeError:
                pass
            return fo.close()

    def is_open(self):
        return bool(self._fo)

    def clone(self, klass=None):
        try:
            newfo = self._fo.dup()
        except AttributeError:
            fd = os.dup(self._fo.fileno())
            newfo = os.fdopen(fd, "w")
        if klass is None:
            klass = self.__class__
        return klass(newfo, prompt=self._prompt, timeout=self.default_timeout,
                     logfile=self._log)

    def interrupt(self):
        """interrupt() sends the INTR character to the stream. Actually,
        delegates this to the wrapped Process object. Otherwise, does nothing.
        """
        try:
            self._fo.interrupt()
        except AttributeError:
            pass

    def closelog(self):
        if self._log:
            self._log.close()
            self._log = None

    def flushlog(self):
        if self._log:
            self._log.flush()

    def setlog(self, fo):
        if hasattr(fo, "write"):
            self._log = fo

    def delay(self, time):
        self.sched.sleep(time)
    sleep = delay

    def wait_for_prompt(self, timeout=None):
        return self.read_until(self._prompt, timeout=timeout)

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, prompt):
        self._prompt = prompt.encode()

    def _get_re(self, patt, mtype=EXACT, callback=None):
        try:
            return self._patt_cache[patt]
        except KeyError:
            if mtype == EXACT:
                self._patt_cache[patt] = p = (compile_exact(patt), callback)
                return p
            elif mtype == GLOB:
                self._patt_cache[patt] = p = (re.compile(fnmatch.translate(patt)),  # noqa
                                              callback)
                return p
            elif mtype == REGEX:
                self._patt_cache[patt] = p = (re.compile(patt), callback)
                return p

    def _get_search_list(self, patt, mtype, callback, solist=None):
        if solist is None:
            solist = []
        ptype = type(patt)
        if isinstance(patt, str):
            solist.append(self._get_re(patt.encode(), mtype, callback))
        elif ptype is tuple:
            solist.append(self._get_re(*patt))
        elif ptype is list:
            list([self._get_search_list(p, mtype, callback, solist)
                  for p in patt])
        elif patt is None:
            return list(self._patt_cache.values())
        return solist

    # the expect method supports a very flexible calling signature. thus,
    # the convoluted type checking, etc.  You may call with a string
    # (defaults to exact string match), or you may supply the match type
    # as a second parameter. Or supply the pattern as a tuple, with
    # string, match type, and callback.  Or, a list of tuples or strings
    # as just described. An optional callback method and timeout value may
    # also be supplied. The callback will be called when a match is found,
    # with a match-object as a parameter.

    def expect(self, patt, mtype=EXACT, callback=None, timeout=None):
        solist = self._get_search_list(patt, mtype, callback)
        if not solist:
            raise ExpectError("Empty expect search.")
        buf = bytes()
        while 1:
            c = self.read(1, timeout)
            if not c:
                raise ExpectError("EOF during expect.")
            buf += c
            self.expectindex = i = -1
            for so, cb in solist:
                mo = so.search(buf)
                if mo:
                    # Save the list index of the match object
                    self.expectindex = i+1
                    if cb:
                        cb(mo)
                    return mo
                i += 1

    def expect_exact(self, patt, callback=None, timeout=None):
        return self.expect(patt, EXACT, callback, timeout)

    def expect_glob(self, patt, callback=None, timeout=None):
        return self.expect(patt, GLOB, callback, timeout)

    def expect_regex(self, patt, callback=None, timeout=None):
        return self.expect(patt, REGEX, callback, timeout)

    def read(self, amt=-1, timeout=None):
        self._timed_out = 0
        timeout = timeout or self.default_timeout
        ev = self.sched.add(timeout, 0, self._timeout_cb, ())
        try:
            while 1:
                try:
                    data = self._fo.read(amt)
                except EnvironmentError as val:
                    if val.errno == EINTR:
                        if self._timed_out == 1:
                            raise scheduler.TimeoutError(
                                "expect: timed out during read.")
                        else:
                            continue
                    else:
                        raise
                except EOFError:
                    return ""
                else:
                    break
        finally:
            self.sched.remove(ev)
        if self._log:
            self._log.write(data)
        return data

    def _timeout_cb(self):
        self._timed_out = 1

    def read_until(self, patt=None, timeout=None):
        if patt is None:
            patt = self._prompt
        buf = ""
        while 1:
            c = self.read(1, timeout)
            if c == "":
                raise ExpectError("EOF during read_until({!r}).".format(patt))
            buf += c
            i = buf.find(patt)
            if i >= 0:
                return buf[:i]

    def readline(self, timeout=None):
        return self.read_until("\n", timeout)

    def readlines(self, N=2147483646, filt=None, timeout=None):
        """Return a list of lines of input. Read up to N lines, optionally
        filterered through a filter function.
        """
        if filt:
            assert isinstance(filt, collections.Callable)
        lines = []
        n = 0
        while n < N:
            line = self.readline(timeout)
            if filt:
                if filt(line):
                    lines.append(line)
                    n += 1
            else:
                lines.append(line)
                n += 1
        return lines

    def isatty(self):
        return os.isatty(self._fo.fileno())

    def ttyname(self):
        return os.ttyname(self._fo.fileno())

    def tcgetpgrp(self):
        return os.tcgetpgrp(self._fo.fileno())

    def fstat(self):
        return os.fstat(self._fo.fileno())

    def seek(self, pos, whence=0):
        return os.lseek(self._fo.fileno(), pos, whence)

    def rewind(self):
        return os.lseek(self._fo.fileno(), 0, 0)

    def clear_cache(self):
        """Clears the pattern cache."""
        self._patt_cache.clear()

    # write methods
    def write(self, data):
        if self._log:
            self._log.write(data)
        return self._fo.write(data)
    send = write

    def send_slow(self, data, delay=0.1):
        for c in data:
            self._fo.write(c)
            self.sched.sleep(delay)

    def writeln(self, text):
        self.write(text+"\n")

    def writeeol(self, text):
        # Prompt is used as EOL when used as state machine
        self.write(text+self._prompt)

    def sendfile(self, filename, wait_for_prompt=0):
        fp = open(filename, "r")
        try:
            self.sendfileobject(fp, wait_for_prompt)
        finally:
            fp.close()

    def sendfileobject(self, fp, wait_for_prompt=0):
        while 1:
            line = fp.read(4096)
            if not line:
                break
            self._fo.write(line)
            if wait_for_prompt:
                self.wait_for_prompt()

    def set_engine(self, engine):
        self._engine = engine

    def step(self):
        next = self.read_until(self._prompt)
        if next:
            self._engine.step(next)
            return True
        return False

    def run(self, engine=None):
        eng = engine or self._engine
        if eng:
            eng.reset()
            while 1:
                next = self.read_until(self._prompt)
                if next:
                    eng.step(next)
                else:
                    break
