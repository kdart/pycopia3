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
Classes and functions for controlling, reading, and writing to co-processes.

"""

import sys
import os
import signal
from signal import SIGCHLD, SIGTERM, SIGSTOP, SIGCONT, SIGHUP, SIG_DFL, SIGINT
from errno import EBADF, EIO

from pycopia import logging
from pycopia import shparser
from pycopia.aid import NULL
from pycopia.OS.procfs import ProcStat
from pycopia.OS.exitstatus import ExitStatus
from pycopia.OS.procutils import run_as
from pycopia.fileutils import close_on_exec, set_nonblocking
from pycopia import scheduler


class ProcessError(Exception):
    pass


class Process:
    """Abstract base class for Processes. Handles all process handling, and
    some common functionality. I/O is handled in subclasses.
    """
    def __init__(self, cmdline, logfile=None, callback=None, async=False):
        self.cmdline = cmdline
        self.deadchild = 0
        self.closed = False
        self.callback = callback  # called at death of process
        self._restart = True  # restart interrupted system calls
        self._buf = b''
        self._errbuf = b''
        self._writebuf = b''
        self.exitstatus = None
        self._environment = None
        self._async = bool(async)  # use asyncio, or not
        self._authtoken = None
        self.logfile = logfile

    def __enter__(self):
        return self

    def __exit__(self, extype, exvalue, traceback):
        self.close()
        return False

    # Override in subclass -- close your file descriptors connected to
    # subprocess.
    def close(self):
        self.closed = True

    def __repr__(self):
        return "{0}({1!r}, async={2!r})".format(
            self.__class__.__name__, self.cmdline, self._async)

    def __str__(self):
        if self.deadchild:
            return str(self.exitstatus)
        else:
            st = self.stat()
            try:
                tty = os.ttyname(self.fileno())
            except:
                tty = "?"
            return "{:6d} {:7s} ({}) {}".format(st.pid, tty, st.statestr(),
                                                 self.cmdline)

    def __int__(self):
        return self.childpid

    def __hash__(self):
        return id(self)

    def restart(self, flag=1):
        old = self._restart
        self._restart = bool(flag)
        return old

    def clone(self):
        """Spawns a copy of this process.
        Note that the log file is not inherited.
        """
        return self.__class__(self.cmdline, env=self.environment,
                              callback=self.callback, async=self._async)

    @property
    def logfile(self):
        """A bytes file-like object that IO will be written to."""
        return self._log

    @logfile.setter
    def logfile(self, newlog):
        if newlog is None:
            self._log = newlog
            return
        newlog.write  # asserts newlog has write method
        try:
            self._log = newlog.buffer
        except AttributeError:
            self._log = newlog

    @logfile.deleter
    def logfile(self):
        self._log = None

    @property
    def environment(self):
        if self._environment is None:
            ps = ProcStat(self.childpid)
            self._environment = ps.environment
        return self._environment

    @environment.setter
    def environment(self, env):
        assert isinstance(env, dict), "Environment must be a dictionary"
        self._environment = env

    @environment.deleter
    def environment(self):
        self._environment = None

    @property
    def basename(self):
        return os.path.basename(self.cmdline.split()[0])

    def kill(self, sig=SIGINT):
        if not self.deadchild:
            self.set_callback(None)  # explicit kill means no restart
            os.kill(self.childpid, sig)

    def killwait(self, sig=SIGINT):
        self.kill(sig)
        return self.wait()

    def stop(self):
        os.kill(self.childpid, SIGSTOP)

    def cont(self):
        os.kill(self.childpid, SIGCONT)
        self.deadchild = 0

    def hangup(self):
        os.kill(self.childpid, SIGHUP)

    def wait(self, option=0):
        """wait() retrieves process exit status. Note that this may block if
        the process is still running.
        """
        if self.exitstatus is not None:
            return self.exitstatus
        else:
            pm = get_procmanager()
            return pm.waitproc(self)

    def setpgid(self, pgid):
        os.setpgid(self.childpid, pgid)

    def set_exitstatus(self, exitstatus):
        self.exitstatus = exitstatus

    def set_callback(self, cb=None):
        """set_callback(cb) Sets the callback function that will be
called when child dies. """
        self.callback = cb

    def dead(self):
        """dead() Called when the child dies. Usually only the
        ProcManager uses this."""
        self.deadchild = 1
        if self.callback:
            self.callback(self)

    def stat(self):
        return ProcStat(self.childpid)

    def fstat(self):
        return os.fstat(self.fileno())

    def isdead(self):
        return self.deadchild

    # Process object considered true if child alive, false if child dead.
    def __bool__(self):
        return not self.deadchild

    def read(self, amt=2147483646):
        if amt < 0:
            amt = 2147483646
        bs = len(self._buf)
        try:
            while bs < amt:
                c = self._read(4096)
                if not c:
                    break
                self._buf += c
                bs = len(self._buf)
        except EOFError:  # TODO log an error
            pass  # let it ruturn rest of buffer
        data = self._buf[:amt]
        self._buf = self._buf[amt:]
        return data

    def readerr(self, amt=2147483646):
        if amt < 0:
            amt = 2147483646
        rs = 1024
        try:
            while len(self._errbuf) < amt:
                c = self._readerr(rs)
                if not c:
                    break
                self._errbuf += c
        except EOFError:
            pass
        amt = min(amt, len(self._errbuf))
        data = self._errbuf[:amt]
        self._errbuf = self._errbuf[amt:]
        return data

# extra fileobject methods.
    def readline(self, amt=2147483646):
        if amt < 0:
            amt = 2147483646
        bufs = []
        rs = min(100, amt)
        while 1:
            c = self.read(rs)
            i = c.find(b"\n")

            if i < 0 and len(c) > amt:
                i = amt-1
            elif amt <= i:
                i = amt-1
            if i >= 0 or c == b'':
                bufs.append(c[:i+1])
                self._unread(c[i+1:])
                return b"".join(bufs)

            bufs.append(c)
            amt -= len(c)
            rs = min(amt, rs*2)

    def readlines(self, sizehint=2147483646):
        if sizehint < 0:
            sizehint = 2147483646
        rv = []
        while sizehint > 0:
            line = self.readline()
            if not line:
                break
            rv.append(line)
            sizehint -= len(line)
        return rv

    def _write_buf(self):
        writ = self._write(self._writebuf)
        self._writebuf = self._writebuf[writ:]
        return writ

    def write(self, data):
        while self._writebuf:
            writ = self._write(self._writebuf)
            self._writebuf = data[writ:]
        writ = self._write(data)
        self._writebuf = data[writ:]
        return writ
    send = write

    def tell(self):
        raise IOError((EBADF, "Process object not seekable"))

    def seek(self, pos, whence=0):
        raise IOError((EBADF, "Process object not seekable"))

    def rewind(self):
        raise IOError((EBADF, "Process object not seekable"))

    def flush(self):
        return None

    def _unread(self, data):
        self._buf = data + self._buf

    # Interface for asyncio poller.
    def readable(self):
        return True

    def writable(self):
        return bool(self._writebuf)

    def priority(self):
        return False

    def read_handler(self):
        data = self._read(16384)
        logging.warning("unhandled read from process")

    def write_handler(self):
        self._write_buf()

    def pri_handler(self):
        pass

    def hangup_handler(self):
        logging.info("Hangup: {}.\n".format(self.cmdline))

    def error_handler(self):
        logging.error(
            "Async handler error occured: {}.\n".format(self.basename))

    def exception_handler(self, ex, val, tb):
        logging.error("Error event: {} ({})\n".format(ex, val))


class ProcessPipe(Process):
    """Process(<commandline>, [<logfile>], [environ])
    Forks and execs a process as given by the command line argument. The
    process's stdio is connected to this instance via pipes, and can be read
    and written to by the instances read() and write() methods.

    """
    def __init__(self, cmdline, logfile=None,  env=None, callback=None,
                 merge=1, pwent=None, async=False, devnull=None, _pgid=0):
        super().__init__(cmdline, logfile, callback, async)
        if env:
            self.environment = env
        cmd = split_command_line(self.cmdline)
        # now, fork the child connected by pipes
        p2cread, self._p_stdin = os.pipe()
        os.set_inheritable(p2cread, True)
        self._p_stdout, c2pwrite = os.pipe()
        os.set_inheritable(c2pwrite, True)
        if merge:
            self._stderr, c2perr = None, None
        else:
            self._stderr, c2perr = os.pipe()
        self.childpid = os.fork()
        self.childpid2 = None  # for compatibility with pipeline
        if self.childpid == 0:
            # Child
            os.setpgid(0, _pgid)
            os.close(0)
            os.close(1)
            os.close(2)
            os.dup2(p2cread, 0)
            os.close(p2cread)
            os.dup2(c2pwrite, 1)
            if merge:
                os.dup2(c2pwrite, 2)
            else:
                os.dup2(c2perr, 2)
                os.close(c2perr)
            os.close(c2pwrite)
            try:
                if pwent:
                    run_as(pwent)
                if env:
                    os.execvpe(cmd[0], cmd, env)
                else:
                    os.execvp(cmd[0], cmd)
            finally:
                os._exit(127)
            # Shouldn't come here
            os._exit(127)
        # parent
        os.close(p2cread)
        os.close(c2pwrite)
        if c2perr:
            os.close(c2perr)

    def isatty(self):
        return os.isatty(self._p_stdin)

    def fileno(self):
        if self._p_stdout is None:
            raise ValueError("I/O operation on closed process")
        return self._p_stdout

    def filenos(self):
        """filenos() Returns tuple of all file descriptors used in this object.
        """
        if self._p_stdout is None:
            raise ValueError("I/O operation on closed process")
        return self._p_stdout, self._p_stdin, self._stderr

    def nonblocking(self, flag=1):
        for fd in self._p_stdout, self._p_stdin, self._stderr:
            set_nonblocking(fd, flag)

    def interrupt(self):
        self.kill(SIGINT)

    def close(self):
        if self.closed:
            return
        super(ProcessPipe, self).close()
        try:
            os.close(self._p_stdin)
        except (TypeError, OSError):
            pass
        try:
            os.close(self._p_stdout)
        except (TypeError, OSError):
            pass
        if self._stderr:
            try:
                os.close(self._stderr)
            except (TypeError, OSError):
                pass
            self._stderr = None
        self._p_stdin = None
        self._p_stdout = None
        self.callback = None  # break a possible reference loop

    def _write(self, data):
        return os.write(self._p_stdin, data)

    def _read_fd(self, fd, length):
        data = os.read(fd, length)
        if self._log is not None:
            self._log.write(data)
        return data

    def _read(self, amt=4096):
        if self._p_stdout is None:
            return b""
        return self._read_fd(self._p_stdout, amt)

    def _readerr(self, amt):
        if self._stderr is None:
            return b""
        return self._read_fd(self._stderr, amt)


class ProcessPty(Process):
    """ProcessPty(<commandline>, [<logfilename>], [environ])
    Forks and execs a process as given by the command line argument. The
    process's stdio is connected to this instance via a pty, and can be read
    and written to by the instances read() and write() methods. That pty
    becomes the processes controlling terminal.
    """
    def __init__(self, cmdline, logfile=None, env=None, callback=None,
                 merge=1, pwent=None, async=False, devnull=False, _pgid=0):
        super().__init__(cmdline, logfile, callback, async)
        if env:
            self.environment = env
        cmd = split_command_line(self.cmdline)
        try:
            pid, self._fd = os.forkpty()
        except OSError as err:
            logging.error("ProcessPty error: {}".format(err))
            raise
        else:
            if pid == 0:  # child
                sys.excepthook = sys.__excepthook__
                if devnull:
                    # Redirect standard file descriptors.
                    sys.stdout.flush()
                    sys.stderr.flush()
                    os.close(sys.__stdin__.fileno())
                    os.close(sys.__stdout__.fileno())
                    os.close(sys.__stderr__.fileno())
                    # stdin always from /dev/null
                    sys.stdin = open("/dev/null", 'r')
                    os.dup2(sys.stdin.fileno(), 0)
                    # log file is stdout and stderr, otherwise /dev/null
                    if logfile is None:
                        sys.stdout = open("/dev/null", 'a+')
                        sys.stderr = open("/dev/null", 'a+', 0)
                        os.dup2(sys.stdout.fileno(), 1)
                        os.dup2(sys.stderr.fileno(), 2)
                    else:
                        so = se = sys.stdout = sys.stderr = logfile
                        os.dup2(so.fileno(), 1)
                        os.dup2(se.fileno(), 2)
                try:
                    if pwent:
                        run_as(pwent)
                    if env:
                        os.execvpe(cmd[0], cmd, env)
                    else:
                        os.execvp(cmd[0], cmd)
                finally:
                    os._exit(127)  # should not be reached

            else:  # parent
                close_on_exec(self._fd)
                self.childpid = pid
                self.childpid2 = None  # for compatibility with pipeline
                self._intr = None
                self._eof = None

    def isatty(self):
        return os.isatty(self._fd)

    def fileno(self):
        if self._fd is None:
            raise ValueError("I/O operation on closed process")
        return self._fd

    def filenos(self):
        """filenos() Returns tuple of all file descriptors used in this object.
        """
        if self._fd is None:
            raise ValueError("I/O operation on closed process")
        return (self._fd,)

    def nonblocking(self, flag=1):
        set_nonblocking(self._fd, flag)

    def interrupt(self):
        """Like pressing Ctl-C on most terminals."""
        if self._intr is None:
            from pycopia import tty
            self._intr = tty.get_intr_char(self._fd)
        self._write(self._intr)

    def send_eof(self):
        """Like pressing Ctl-D on most terminals."""
        if self._eof is None:
            from pycopia import tty
            self._eof = tty.get_eof_char(self._fd)
        self._write(self._eof)

    def close(self):
        if self.closed:
            return
        super(ProcessPty, self).close()
        try:
            os.close(self._fd)
        except (TypeError, OSError):
            pass
        self._fd = None
        self.callback = None  # break a possible reference loop

    def _write(self, data):
        return os.write(self._fd, data)

    def _read(self, length=100):
        data = os.read(self._fd, length)
        if self._log is not None:
            self._log.write(data)
        return data


class CoProcessPty(ProcessPty):
    def __init__(self, method, logfile=None, env=None,
                 callback=None, async=False, pwent=None, _pgid=0):
        super().__init__("python: %s" % (method.__name__,),
                         logfile, callback, async)
        pid, self._fd = os.forkpty()
        self.childpid = pid
        self.childpid2 = None  # for compatibility with pipeline
        if pid == 0 and pwent:
            run_as(pwent)


class CoProcessPipe(ProcessPipe):
    def __init__(self, method, logfile=None, env=None,
                 callback=None, merge=False, async=False, pwent=None, _pgid=0):
        super().__init__("python <=> %s" % (method.__name__,), logfile,
                         callback, async)

        p2cread, self._p_stdin = os.pipe()
        os.set_inheritable(p2cread, True)
        self._p_stdout, c2pwrite = os.pipe()
        os.set_inheritable(c2pwrite, True)
        if merge:
            self._stderr, c2perr = None, None
        else:
            self._stderr, c2perr = os.pipe()
            os.set_inheritable(c2perr, True)
        self.childpid = os.fork()
        self.childpid2 = None
        if self.childpid == 0:
            try:
                # Child
                os.close(0)
                os.close(1)
                os.close(2)
                os.dup2(p2cread, 0)
#                sys.stdin = os.fdopen(0, mode="r")
                os.dup2(c2pwrite, 1)
#                sys.stdout = os.fdopen(1, mode="w")
                if merge:
                    os.dup2(c2pwrite, 2)
#                    sys.stderr = os.fdopen(2, mode="w")
                else:
                    os.dup2(c2perr, 2)
#                    sys.stderr = os.fdopen(2, mode="w")
                if pwent:
                    run_as(pwent)
            except Exception:
                logging.exception_error("CoProcessPipe")
        os.close(p2cread)
        os.close(c2pwrite)
        if c2perr:
            os.close(c2perr)


# simply forks this python process
class SubProcess(Process):
    def __init__(self, pwent=None, _pgid=0):
        super().__init__(sys.argv[0])
        pid = os.fork()
        if pid == 0:
            sys.excepthook = sys.__excepthook__  # remove any debugger hook
            if pwent:
                run_as(pwent)
        self.childpid = pid
        self.childpid2 = None  # for compatibility with pipeline


# TODO need a more general pipeline
class ProcessPipeline(ProcessPipe):
    """Connects two commands via a pipe, they appear as one process object."""
    def __init__(self, cmdline, logfile=None,  env=None, callback=None,
                 merge=None, pwent=None, async=False, devnull=None, _pgid=0):
        assert cmdline.count("|") == 1
        [cmdline1, cmdline2] = cmdline.split("|")
        if env:
            self.environment = env
        super().__init__(cmdline2, logfile, callback, async)
        self._stderr = None

        cmd1 = split_command_line(cmdline1)
        cmd2 = split_command_line(cmdline2)

        # self._p_stdin -> cmd1 -> p_write|p_read -> cmd2 -> self._p_stdout

        _p_stdout, self._p_stdin = os.pipe()
        p_read, p_write = os.pipe()
        self._p_stdout, _p_stdin = os.pipe()

        self.childpid = os.fork()
        # cmd1
        if self.childpid == 0:
            # Child 1
            os.dup2(_p_stdout, 0)
            os.dup2(p_write, 1)
            self._exec(cmd1, env, pwent)
            os._exit(127)

        # cmd2
        cmd2pid = os.fork()
        if cmd2pid == 0:
            # Child 2
            os.dup2(p_read, 0)
            os.dup2(_p_stdin, 1)
            self._exec(cmd2, env, pwent)
            os._exit(127)

        self.childpid2 = cmd2pid
        # close our copies
        os.close(_p_stdout)
        os.close(_p_stdin)
        os.close(p_read)
        os.close(p_write)

    def _exec(self, cmd, env, pwent):
        # close all other file descriptors for child.
        if pwent:
            run_as(pwent)
        if env:
            os.execvpe(cmd[0], cmd, env)
        else:
            os.execvp(cmd[0], cmd)


class ProcManager(object):
    """An instance of ProcManager manages a collection of child processes. It
is a singleton, and you should use the get_procmanager() factory function
to get the instance.  """

    def __init__(self):
        self._pgid = os.getpgid(0)
        self._procs = {}
        signal.signal(SIGCHLD, self._child_handler)
        signal.siginterrupt(SIGCHLD, False)

    def __len__(self):
        return len(self._procs)

    def __str__(self):
        s = []
        for p in self.getprocs():
            s.append(str(p))
        return "\n".join(s)

    def spawnprocess(self, pklass, cmd, logfile=None, env=None, callback=None,
                     persistent=False, merge=True, pwent=None, async=False,
                     devnull=False):
        """Start a child process using a user supplied subclass of ProcessPty
        or ProcessPipe.
        """

        if persistent and (callback is None):
            callback = self.respawn_callback
        signal.signal(SIGCHLD, SIG_DFL)  # critical area
        proc = pklass(cmd, logfile=logfile, env=env, callback=callback,
                      merge=merge, pwent=pwent, async=async, devnull=devnull,
                      _pgid=self._pgid)
        self._procs[proc.childpid] = proc
        # TODO need a more general pipeline
        if proc.childpid2:
            self._procs[proc.childpid2] = proc
        signal.signal(SIGCHLD, self._child_handler)
        signal.siginterrupt(SIGCHLD, False)
        return proc

    def spawnpipe(self, cmd, logfile=None, env=None, callback=None,
                  persistent=False, merge=True, pwent=None, async=False,
                  devnull=False):
        """Start a child process, connected by pipes."""
        if cmd.find("|") > 0:
            klass = ProcessPipeline
        else:
            klass = ProcessPipe
        return self.spawnprocess(klass, cmd, logfile, env, callback,
                                 persistent, merge, pwent, async, devnull)

    # default spawn method
    spawn = spawnpipe

    def spawnpty(self, cmd, logfile=None, env=None, callback=None,
                 persistent=False, merge=True, pwent=None, async=False,
                 devnull=False):
        """Start a child process using a pty. The <persistent> variable is the
        number of times the process will be respawned if the previous
        invocation dies.
        """
        return self.spawnprocess(ProcessPty, cmd, logfile, env, callback,
                                 persistent, merge, pwent, async, devnull)

    def coprocess(self, method, args=(), logfile=None, env=None, callback=None,
                  async=False):
        signal.signal(SIGCHLD, SIG_DFL)  # critical area
        proc = CoProcessPipe(method, logfile=logfile, env=env,
                             callback=callback, async=async)
        if proc.childpid == 0:
            os.setpgid(0, self._pgid)
            sys.excepthook = sys.__excepthook__
            # child is not managing any of these
            self._procs.clear()
            try:
                rv = method(*args)
            except SystemExit as val:
                rv = int(val)
            except Exception:
                logging.exception_error("coprocess")
                rv = 127
            if rv is None:
                rv = 0
            try:
                rv = int(rv)
            except:
                rv = 0
            os._exit(rv)
        self._procs[proc.childpid] = proc
        signal.signal(SIGCHLD, self._child_handler)
        signal.siginterrupt(SIGCHLD, False)
        return proc

    def subprocess(self, _method, *args, **kwargs):
        return self.submethod(_method, args, kwargs)

    def submethod(self, _method, args=None, kwargs=None, pwent=None):
        args = args or ()
        kwargs = kwargs or {}
        signal.signal(SIGCHLD, SIG_DFL)  # critical area
        proc = SubProcess(pwent=pwent)
        if proc.childpid == 0:  # in child
            os.setpgid(0, self._pgid)
            sys.excepthook = sys.__excepthook__
            self._procs.clear()
            try:
                rv = _method(*args, **kwargs)
            except SystemExit as val:
                rv = val.code
            except:
                ex, val, tb = sys.exc_info()
                try:
                    import traceback
                    try:
                        fname = _method.__name__
                    except AttributeError:
                        try:
                            fname = _method.__class__.__name__
                        except AttributeError:
                            fname = str(_method)
                    with open("/tmp/" + fname + "_error.log", "w+") as errfile:
                        traceback.print_exception(ex, val, tb, None, errfile)
                finally:
                    ex = val = tb = None
                rv = 127
            if rv is None:
                rv = 0
            try:
                rv = int(rv)
            except:
                rv = 0
            os._exit(rv)
        else:
            self._procs[proc.childpid] = proc
            signal.signal(SIGCHLD, self._child_handler)
            signal.siginterrupt(SIGCHLD, False)
            return proc

    # introspection and query methods
    def getpids(self):
        """getpids() Returns a list of managed PIDs (which are integers)."""
        return list(self._procs.keys())

    def getprocs(self):
        """getprocs() Returns a list of managed process objects."""
        return list(self._procs.values())

    def getbyname(self, name):
        """getbyname(procname) Returns a list of process objects that match the
        given name.
        """
        name = os.path.basename(name)
        return [p for p in list(self._procs.values()) if p.basename == name]

    def getbypid(self, pid):
        """getbypid(pid) Returns the process object that matches the given PID.
        """
        try:
            return self._procs[pid]
        except KeyError:
            return None

    def getstats(self):
        """getstats() Returns a list of process status objects (ProcStat) for
        each managed process.
        """
        return [ProcStat(o) for o in list(self._procs.keys())]

    def killall(self, name=None, sig=SIGTERM):
        """Kills all managed processes with the name 'name'. If 'name' not
        given kill ALL processes. Default signal is SIGTERM.
        """
        if name is None:
            procs = list(self._procs.values())
        else:
            procs = self.getbyname(name)
        for p in procs:
            p.close()
            p.kill(sig)

    def kill(self, proc, sig=SIGINT):
        proc.kill(sig)

    def stopall(self):
        """Sends STOP to all managed processes. To restart get the
        process objects and invoke the cont() method.
        """
        for p in list(self._procs.values()):
            p.stop()

    def clone(self, proc=None):
        """clone([proc]) clones the supplied process object and manages it as
        well. If no process object is supplied then clone the first managed
        process found in this ProcManager.
        """
        if proc is None:  # default to cloning first process found.
            procs = list(self._procs.values())
            if procs:
                proc = procs[0]
                del procs
            else:
                return
        signal.signal(SIGCHLD, SIG_DFL)  # critical area
        newproc = proc.clone()
        self._procs[newproc.childpid] = newproc
        signal.signal(SIGCHLD, self._child_handler)
        signal.siginterrupt(SIGCHLD, False)
        return newproc

    def respawn_callback(self, deadproc):
        """Callback that performs a respawn, for persistent services."""
        if deadproc.exitstatus.status == 127:
            logging.error("process {!r} didn't start (NOT restarting).\n".format(  # noqa
                deadproc.cmdline))
            raise ProcessError("Process never started. Check command line.")
        elif not deadproc.exitstatus:
            logging.error("process {!r} died: %s (restarting in 1 sec.).\n".format(  # noqa
                         deadproc.cmdline, deadproc.exitstatus))
            scheduler.add(self._respawn, 1.0, args=(deadproc,))
        else:
            logging.info("process {!r} normal exit (NOT restarting).\n".format(
                    deadproc.cmdline))
        return None

    def _respawn(self, deadproc):
        new = self.clone(deadproc)
        new._log = deadproc._log

    # this is the SIGCHLD signal handler
    def _child_handler(self, sig, stack):
        pid, sts = os.waitpid(-1, os.WNOHANG)
        proc = self._procs.get(pid)
        if proc is not None:
            self._proc_status(proc, sts)
        signal.signal(SIGCHLD, self._child_handler)
        signal.siginterrupt(SIGCHLD, False)

    def waitpid(self, pid, option=0):
        try:
            proc = self._procs[pid]
        except KeyError:
            logging.warning("Wait on unmanaged process (pid: %s)." % pid)
            cmdline = ProcStat(pid).cmdline
            pid, sts = os.waitpid(pid, option)
            return ExitStatus(sts, cmdline.split()[0])
        return self.waitproc(proc)

    def waitproc(self, proc, option=0):  # waits for a Process object.
        """waitproc(process, [option])
        Waits for a process object to finish. Depends on signal handler.
        """
        if proc.exitstatus is not None:
            return proc.exitstatus
        signal.signal(SIGCHLD, SIG_DFL)
        try:
            pid, sts = os.waitpid(proc.childpid, option)
        finally:
            signal.signal(SIGCHLD, self._child_handler)
            signal.siginterrupt(SIGCHLD, False)
        return self._proc_status(proc, sts)

    def _proc_status(self, proc, sts):
        es = ExitStatus(sts, proc.cmdline.split()[0])
        proc.set_exitstatus(es)
        # XXX untested with stopped processes
        if es.state != ExitStatus.STOPPED:
            proc.dead()
            del self._procs[proc.childpid]
        return es

    def loop(self, poller, timeout=-1.0, callback=NULL):
        while self._procs:
            poller.poll(timeout)
            callback(self)
            if scheduler.get_scheduler():  # wait for any restarts
                scheduler.sleep(1.5)


def get_procmanager():
    """get_procmanager() returns the procmanager. A ProcManager is a singleton
instance. Always use this factory function to get it."""
    global procmanager
    try:
        return procmanager
    except NameError:
        procmanager = ProcManager()
    return procmanager


def remove_procmanager():
    global procmanager
    signal.signal(SIGCHLD, SIG_DFL)
    del procmanager


#  Process manager factory functions
def spawnpipe(cmd, logfile=None, env=None, callback=None,
              persistent=False, merge=True, pwent=None, async=False):
    """Start a child process, connected by pipes.
    """
    pm = get_procmanager()
    proc = pm.spawnpipe(cmd, logfile, env, callback, persistent, merge, pwent,
                        async)
    return proc


def spawnpty(cmd, logfile=None, env=None, callback=None,
             persistent=False, merge=True, pwent=None, async=False,
             devnull=False):
    """Start a child process using a pty.
    """
    pm = get_procmanager()
    proc = pm.spawnpty(cmd, logfile, env, callback, persistent, merge, pwent,
                       async, devnull)
    return proc


def coprocess(func, args=(), logfile=None, env=None, callback=None,
              async=False):
    """Works like fork(), but connects the childs stdio to a pty. Returns a
    file-like object connected to the master end of the child pty.
    """
    pm = get_procmanager()
    cp = pm.coprocess(func, args, logfile, env, callback, async)
    return cp


def waitproc(proc, option=0):
    pm = get_procmanager()
    return pm.waitproc(proc, option)


def subprocess(method, *args, **kwargs):
    pm = get_procmanager()
    return pm.subprocess(method, *args, **kwargs)


def submethod(_method, args=None, kwargs=None, pwent=None):
    pm = get_procmanager()
    return pm.submethod(_method, args, kwargs, pwent)


def getstatusoutput(cmd, logfile=None, env=None, callback=None):
    p = spawnpipe(cmd, logfile, env, callback)
    text = p.read()
    p.wait()
    return p.exitstatus, text


def call(*args, **kwargs):
    return spawnpipe(*args, **kwargs).wait()


def setpgid(pid_or_proc, pgrp):
    pid = int(pid_or_proc)
    return os.setpgid(pid, pgrp)


split_command_line = shparser.get_command_splitter()
