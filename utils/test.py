#!/usr/bin/python2.7
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division
"""
"""

import unittest
import signal
import time
import os

import readline
import fcntl
import mmap
from pycopia import timers

s = time.time()

def catcher(n,f):
    global s
    print('Alarmed in %.4f' % ( time.time() - s ))
    s = time.time()

class UtilsTests(unittest.TestCase):

    def test_alarm(self):
        global s
        signal.signal(signal.SIGALRM, catcher)
        start = s = time.time()
        try:
            timers.alarm(2.5)
            signal.pause()
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        self.assertAlmostEqual(time.time()-start, 2.5, places=2)

    def test_nanosleep(self):
        global s
        signal.signal(signal.SIGALRM, catcher)
        start = s = time.time()
        try:
            signal.alarm(2)
            timers.nanosleep(10.0)
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        self.assertAlmostEqual(time.time()-start, 10.0, places=2)

    def test_absolutesleep(self):
        global s
        signal.signal(signal.SIGALRM, catcher)
        start = s = time.time()
        try:
            signal.alarm(2)
            timers.absolutesleep(start + 10.0)
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        self.assertAlmostEqual(time.time()-start, 10.0, places=2)

    def test_FDTimer(self):
        t = timers.FDTimer()
        self.assertFalse(t)
        t.settime(5.0, 2.0)
        self.assertTrue(t)
        start = time.time()
        print(t.read())
        self.assertAlmostEqual(time.time()-start, 5.0, places=2)
        print(t.read())
        self.assertAlmostEqual(time.time()-start, 7.0, places=2)
        print(t.read())
        self.assertAlmostEqual(time.time()-start, 9.0, places=2)
        t.close()
        self.assertFalse(t)
        self.assertTrue(t.closed)

    def test_FDTimer_absolute(self):
        t = timers.FDTimer(timers.CLOCK_REALTIME)
        start = time.time()
        t.settime(time.clock_gettime(time.CLOCK_REALTIME)+5.0, 0.0, absolute=True)
        print(t.read())
        t.close()
        self.assertAlmostEqual(time.time()-start, 5.0, places=2)

    def test_timer_create(self):
        global _t
        _t = timers.IntervalTimer(signal.SIGRTMIN, timers.CLOCK_MONOTONIC)
        print(repr(_t))
        print(_t)

    def test_timer_cset(self):
        global _t
        signal.signal(signal.SIGRTMIN, catcher)
        now = time.monotonic()
        try:
            _t.settime(now + 2.5, absolute=True)
            timers.nanosleep(1.0)
            print(_t.gettime())
            signal.pause()
            print(_t.gettime())
            _t.settime(0, absolute=True)
        finally:
            signal.signal(signal.SIGRTMIN, signal.SIG_DFL)
        self.assertAlmostEqual(time.monotonic()-now, 2.5, places=2)

    def test_timer_csoverruns(self):
        global _t
        ov = _t.getoverrun()
        print(_t.getoverrun())
        self.assertEqual(ov, 0)

    def test_timer_delete(self):
        global _t
        del _t


if __name__ == '__main__':
    unittest.main()
