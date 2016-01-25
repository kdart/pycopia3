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
A library for scheduling callback functions using timers and realtime signals.

"""

__all__ = ['TimeoutError', 'SchedulerError', 'Scheduler', 'get_scheduler',
           'del_scheduler', 'timeout', 'iotimeout', 'add', 'repeat']

from pycopia import timers

# expose here some timers functions.
sleep = timers.nanosleep


class TimeoutError(Exception):
    pass


class SchedulerError(Exception):
    pass



def _cb_adapter(func, args, kwargs):
    def _cb(sig, stack):
        return func(*args, **kwargs)
    return _cb


class Scheduler:
    """A Scheduler instance uses per-process timers to manage a collection of
    delayed or periodic functions.
    """
    def __init__(self):
        self._timers = [None] * 32
        self._index = 1

    def __bool__(self):
        return any(self._timers)

    def add(self, callback, delay, interval=0, args=None, kwargs=None):
        """Add a callback with delay and interval.
        """
        args = tuple(args or ())
        kwargs = dict(kwargs or {})
        index = self._index + 1
        raise NotImplementedError()

    def remove(self, handle):
        """remove(handle)
        Removes the event from the event queue. The event is an Event object as
        returned by the add method."""
        try:
            timer, oldhandler = self._timers[handle]
        except (ValueError, IndexError, TypeError):
            raise SchedulerError("Bad handle to remove")
        raise NotImplementedError()

    def stop(self):
        """Stop and remove all timers."""
        raise NotImplementedError()

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
        raise NotImplementedError()

    def iotimeout(self, function, args=(), kwargs=None, timeout=30):
        """Wraps any IO function that may block in the kernel. Provides a
        timeout feature."""
        raise NotImplementedError()


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
    s = get_scheduler()
