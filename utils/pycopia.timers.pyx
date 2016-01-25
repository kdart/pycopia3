# python wrapper for interruptable sleepers, and timerfd interface.
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2014-  Keith Dart <keith@kdart.com>
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


from posix.unistd cimport close, read

cdef extern from "Python.h":
    int PyErr_CheckSignals()


cdef extern from "signal.h" nogil:

    cdef union sigval:
        int sival_int
        void *sival_ptr
    ctypedef sigval sigval_t

    cdef struct sigevent:
        sigval_t sigev_value
        int sigev_signo
        int sigev_notify
    ctypedef sigevent sigevent_t

    enum:SIGEV_SIGNAL

cdef extern from "time.h" nogil:

    cdef struct timeval:
       long int tv_sec
       long int tv_usec

    cdef struct itimerval:
       timeval it_interval
       timeval it_value

    cdef struct timespec:
       long int tv_sec
       long int tv_nsec

    cdef struct itimerspec:
        timespec it_interval
        timespec it_value

    ctypedef void *timer_t

    int setitimer (int, itimerval *, itimerval *)
    int c_nanosleep "nanosleep" (timespec *, timespec *)
    int clock_nanosleep(int clock_id, int flags, timespec *rqtp, timespec *rmtp)


    IF UNAME_SYSNAME == "Linux":
        int timer_create (int, sigevent *, timer_t *)
        int timer_delete (timer_t)
        int timer_settime (timer_t, int, const itimerspec *, itimerspec * )
        int timer_gettime (timer_t, itimerspec *)
        int timer_getoverrun(timer_t)

        enum:TIMER_ABSTIME
        enum:ITIMER_REAL


IF UNAME_SYSNAME == "Linux":
    cdef extern from "sys/timerfd.h":
        int timerfd_create (int, int)
        int timerfd_settime (int, int, itimerspec *, itimerspec *)
        int timerfd_gettime (int, itimerspec *)

        enum:TFD_CLOEXEC
        enum:TFD_NONBLOCK
        enum:TFD_TIMER_ABSTIME


cdef extern from "string.h":
    char *strerror(int errnum)

cdef extern from "errno.h":
    int errno
    enum:EINTR

cdef extern double floor(double)
cdef extern double fmod(double, double)


cdef inline void _set_timespec(timespec *ts, double n):
    ts.tv_sec = <long> floor(n)
    ts.tv_nsec = <long> (fmod(n, 1.0) * 1000000000.0)


def nanosleep(double delay):
    """Sleep for <delay> seconds, with nanosecond precision. Unlike
    time.sleep(), signal handlers are run during this sleep."""
    cdef timespec ts_delay

    _set_timespec(&ts_delay, delay)
    while c_nanosleep(&ts_delay, &ts_delay) == -1:
        if errno == EINTR:
            PyErr_CheckSignals()
        else:
            raise OSError((errno, strerror(errno)))
    return 0


IF UNAME_SYSNAME == "Linux":

    CLOCK_REALTIME = 0
    CLOCK_MONOTONIC = 1
    DEF CLOCK_REALTIME = 0
    DEF CLOCK_MONOTONIC = 1


    class ItimerError(Exception):
      pass

    cdef inline double _timeval2float(timeval *tv):
        return <double> tv.tv_sec + (<double> tv.tv_usec / 1000000.0)

    cdef inline double _timespec2float(timespec *tv):
        return <double> tv.tv_sec + (<double> tv.tv_nsec / 1000000000.0)

    cdef inline void _set_timeval(timeval *tv, double n):
        tv.tv_sec = <long> floor(n)
        tv.tv_usec = <long> (fmod(n, 1.0) * 1000000.0)

    def absolutesleep(double time, int clockid=CLOCK_REALTIME):
        """Sleep until <time> (unix time), with nanosecond precision. Signal
        handlers are run while sleeping."""
        cdef timespec ts_delay
        cdef int rv

        _set_timespec(&ts_delay, time)
        while 1:
            rv = clock_nanosleep(clockid, TIMER_ABSTIME, &ts_delay, NULL)
            if rv == EINTR:
                PyErr_CheckSignals()
            elif rv == 0:
                return 0
            else:
                raise OSError((rv, strerror(rv)))


    def alarm(double delay):
        """Arrange for SIGALRM to arrive after the given number of seconds.
    The argument may be floating point number for subsecond precision. Returns
    the original value of the timer, as a float.
        """
        cdef itimerval new
        cdef itimerval old

        _set_timeval(&new.it_value, delay)
        new.it_interval.tv_sec = new.it_interval.tv_usec = 0
        if setitimer(ITIMER_REAL, &new, &old) == -1:
            raise ItimerError("Could not set itimer for alarm")
        return _timeval2float(&old.it_value)



    cdef extern from "stdint.h":
    #if __WORDSIZE == 64
        ctypedef unsigned long int uint64_t
    #else
        ctypedef unsigned long long int uint64_t
    #endif


    cdef class FDTimer:
        """FDTimer(clockid=CLOCK_MONOTONIC, nonblocking=0)
        A timer that is a file-like object. It may be added to select or poll. A
        read returns the number of times timer has expired since last read. See
        timerfd_create(2) for more information.
        If nonblocking flag is true, the fd is made non-blocking.
        """
        cdef int _fd

        def __init__(self, int clockid=CLOCK_MONOTONIC, int nonblocking=0):
            cdef int fd = -1
            fd = timerfd_create(clockid, TFD_CLOEXEC | TFD_NONBLOCK if nonblocking else 0)
            if fd == -1:
                raise OSError((errno, strerror(errno)))
            self._fd = fd

        def __dealloc__(self):
            self.close()

        def __nonzero__(self):
            cdef itimerspec ts
            if self._fd == -1:
                return False
            if timerfd_gettime(self._fd, &ts) == -1:
                raise OSError((errno, strerror(errno)))
            return not (ts.it_value.tv_sec == 0 and ts.it_value.tv_nsec == 0 and
                    ts.it_interval.tv_sec == 0 and ts.it_interval.tv_nsec == 0)

        def close(self):
            if self._fd != -1:
                close(self._fd)
                self._fd = -1

        def fileno(self):
            return self._fd

        property closed:
            def __get__(self):
                return self._fd == -1

        def settime(self, double expire, double interval=0.0, int absolute=0):
            """settime(expire, interface, absolute=0)
        Set time for initial timeout, and subsequent intervals. Set interval to
        zero for one-shot timer. Set expire time to zero to disarm. The time is
        absolute (unix time) if the absolute flag is true.
        Returns current time value and interval at time of the call.
            """
            cdef itimerspec ts
            cdef itimerspec old
            cdef timespec ts_interval
            cdef timespec ts_expire
            _set_timespec(&ts_expire, expire)
            _set_timespec(&ts_interval, interval)
            ts.it_interval = ts_interval
            ts.it_value = ts_expire
            if timerfd_settime(self._fd, TFD_TIMER_ABSTIME if absolute else 0, &ts, &old) == -1:
                raise OSError((errno, strerror(errno)))
            return _timespec2float(&old.it_value), _timespec2float(&old.it_interval)

        def gettime(self):
            """gettime()
        Returns tuple of (time until next expiration, interval).
            """
            cdef itimerspec ts
            if timerfd_gettime(self._fd, &ts) == -1:
                raise OSError((errno, strerror(errno)))
            return _timespec2float(&ts.it_value), _timespec2float(&ts.it_interval)

        def read(self, int amt=-1):
            """read(amt=-1)
        Returns number of times timer has expired since last read.
        The amt parameter is for file-like type compatibility, and is ignored."""
            cdef uint64_t buf
            cdef int rv
            while 1:
                rv = read(self._fd, &buf, 8)
                if rv == 8:
                    return <unsigned long long> buf
                elif rv == -1 and errno == EINTR:
                    PyErr_CheckSignals()
                else:
                    raise OSError((errno, strerror(errno)))



    cdef class IntervalTimer:
        """IntervalTimer(signo, clockid=CLOCK_MONOTONIC)
        POSIX per-process interval timers,
        signum is the signal to use when expiring.

        """
        cdef timer_t _timerid
        cdef int _clocktype
        cdef int _thesig

        def __init__(self, int signo, int clockid=CLOCK_MONOTONIC):
            cdef sigevent_t sev

            sev.sigev_notify = SIGEV_SIGNAL
            sev.sigev_signo = signo
            sev.sigev_value.sival_ptr = &self._timerid
            while 1:
                rv = timer_create(clockid, &sev, &self._timerid)
                if rv == EINTR:
                    PyErr_CheckSignals()
                elif rv == 0:
                    self._clocktype = clockid
                    self._thesig = signo
                    return
                else:
                    raise OSError((rv, strerror(rv)))

        property signo:
            "signal number"
            def __get__(self):
                return self._thesig

        property id:
            "timer identifier"
            def __get__(self):
                return <long> self._timerid

        property clockid:
            "clockid (type)"
            def __get__(self):
                return self._clocktype

        def __dealloc__(self):
            timer_delete(self._timerid)

        def __repr__(self):
            return "IntervalTimer({0:d}. {1:d})".format(self._thesig, self._clocktype)

        def __str__(self):
            return "IntervalTimer: signo: {0:d} clockid: {1:d} id: {2:X}".format(
                    self._thesig, self._clocktype, <long> self._timerid)

        def settime(self, double expire, double interval=0.0, absolute=False):
            """Set expire time and interval time.
            Returns the tuple (timeremaining, interval).
            """
            cdef itimerspec new_value
            cdef itimerspec old_value
            cdef timespec ts_interval
            cdef timespec ts_expire

            _set_timespec(&ts_expire, expire)
            _set_timespec(&ts_interval, interval)
            new_value.it_interval = ts_interval
            new_value.it_value = ts_expire
            rv = timer_settime(self._timerid, TIMER_ABSTIME if absolute else 0, &new_value, &old_value)
            if rv == 0:
                return _timespec2float(&old_value.it_value), _timespec2float(&old_value.it_interval)
            else:
                raise OSError((rv, strerror(rv)))

        def gettime(self):
            """Return current expire time and interval time."""
            cdef itimerspec ts

            rv = timer_gettime(self._timerid, &ts)
            if rv == 0:
                return _timespec2float(&ts.it_value), _timespec2float(&ts.it_interval)
            else:
                raise OSError((rv, strerror(rv)))

        def getoverrun(self):
            return timer_getoverrun(self._timerid)


