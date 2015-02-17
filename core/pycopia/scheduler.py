#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 1999-  Keith Dart <keith@kdart.com>
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
A library for scheduling callback functions using timers and realtime signals.

"""

__all__ = ['TimeoutError', 'SchedulerError', 'Scheduler', 'get_scheduler',
           'del_scheduler', 'timeout', 'iotimeout', 'add', 'repeat']

import signal

from pycopia import timers

# expose here some timers functions.
alarm = timers.alarm
sleep = timers.nanosleep


class TimeoutError(Exception):
    pass


class SchedulerError(Exception):
    pass


SIGMAX = signal.SIGRTMAX - signal.SIGRTMIN


def _cb_adapter(func, args, kwargs):
    def _cb(sig, stack):
        return func(*args, **kwargs)
    return _cb


class Scheduler:
    """A Scheduler instance uses per-process timers to manage a collection of
    delayed or periodic functions.
    """
    def __init__(self):
        self._timers = [None] * SIGMAX
        self._index = 1

    def __bool__(self):
        return any(self._timers)

    def add(self, callback, delay, interval=0, args=None, kwargs=None):
        """Add a callback with delay and interval.
        """
        args = tuple(args or ())
        kwargs = dict(kwargs or {})
        index = self._index + 1
        if index > SIGMAX:
            raise SchedulerError("Maximum timed events reached")
        signum = signal.SIGRTMIN+index
        oldhandler = signal.signal(signum, _cb_adapter(callback, args, kwargs))
        signal.siginterrupt(signum, False)
        timer = timers.IntervalTimer(signum)
        timer.settime(float(delay), float(interval))
        self._timers[index] = (timer, oldhandler)
        self._index = index
        return index

    def remove(self, handle):
        """remove(handle)
        Removes the event from the event queue. The event is an Event object as
        returned by the add method."""
        try:
            timer, oldhandler = self._timers[handle]
        except (ValueError, IndexError, TypeError):
            raise SchedulerError("Bad handle to remove")
        timer.settime(0.0)
        self._timers[handle] = None
        signal.signal(timer.signo, oldhandler)

    def stop(self):
        """Stop and remove all timers."""
        for i in range(SIGMAX):
            try:
                self.remove(i)
            except SchedulerError:
                pass

    def sleep(self, delay):
        """sleep(<secs>)
        Pause the current thread of execution for <secs> seconds. Use this
        instead of time.sleep() since it works with the scheduler, and allows
        other events to run.  """
        sleep(delay)

    def _timeout_cb(self, sig, st):
        raise TimeoutError("timer expired")

    def timeout(self, function, args=(), kwargs=None, timeout=30):
        """Wraps a function. Will raise TimeoutError if the alloted time is
        reached before the function exits.
        """
        signum = signal.SIGRTMIN
        oldhandler = signal.signal(signum, self._timeout_cb)
        signal.siginterrupt(signum, False)
        timer = timers.IntervalTimer(signum)
        timer.settime(float(timeout))
        try:
            return function(*args, **kwargs)
        finally:
            timer.settime(0.0)
            signal.signal(signum, oldhandler)

    def iotimeout(self, function, args=(), kwargs=None, timeout=30):
        """Wraps any IO function that may block in the kernel. Provides a
        timeout feature."""
        self._timed_out = 0
        signum = signal.SIGRTMIN+1
        oldhandler = signal.signal(signum, self._timedio_cb)
        signal.siginterrupt(signum, True)
        timer = timers.IntervalTimer(signum)
        timer.settime(float(timeout))
        kwargs = kwargs or {}
        try:
            while 1:
                try:
                    return function(*args, **kwargs)
                except InterruptedError:
                    if self._timed_out:
                        raise TimeoutError("IO timed out")
                    else:
                        continue
        finally:
            timer.settime(0.0)
            signal.signal(signum, oldhandler)

    def _timedio_cb(self, sig, stack):
        self._timed_out = 1


scheduler = None


# alarm schedulers are singleton instances. Only use this factory function to
# get it.
def get_scheduler():
    global scheduler
    if scheduler is None:
        scheduler = Scheduler()
    return scheduler


def del_scheduler():
    global scheduler
    if scheduler is not None:
        scheduler.stop()
        scheduler = None


def timeout(*args, **kwargs):
    return get_scheduler().timeout(*args, **kwargs)


def iotimeout(*args, **kwargs):
    return get_scheduler().iotimeout(*args, **kwargs)


def add(callback, delay, args=()):
    return get_scheduler().add(callback, delay, args=args)


def repeat(method, interval, *args):
    s = get_scheduler()
    return s.add(method, interval, interval, args=args)


if __name__ == "__main__":
    def cb():
        print("cb called")

    def cb2():
        print("cb2 called")

    s = get_scheduler()
    print("starting in 5 secs")
    h = s.add(cb, 5, 2)
    h2 = s.add(cb2, 6, 2)
    s.sleep(10)
    s.remove(h)
    s.sleep(6)
    s.remove(h2)
    print("done")
