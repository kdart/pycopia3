#!/usr/bin/python2.7
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 1999- Keith Dart <keith@kdart.com>
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

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division
"""
"""

import unittest
import signal
import time

import readline
import fcntl
import mmap
from pycopia import fdtimer

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
            fdtimer.alarm(2.5)
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
            fdtimer.nanosleep(10.0)
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        self.assertAlmostEqual(time.time()-start, 10.0, places=2)

    def test_absolutesleep(self):
        global s
        signal.signal(signal.SIGALRM, catcher)
        start = s = time.time()
        try:
            signal.alarm(2)
            fdtimer.absolutesleep(start + 10.0)
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        self.assertAlmostEqual(time.time()-start, 10.0, places=2)

    def test_FDTimer(self):
        t = fdtimer.FDTimer()
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
        t = fdtimer.FDTimer(fdtimer.CLOCK_REALTIME)
        start = time.time()
        t.settime(time.clock_gettime(time.CLOCK_REALTIME)+5.0, 0.0, absolute=True)
        print(t.read())
        t.close()
        self.assertAlmostEqual(time.time()-start, 5.0, places=2)

if __name__ == '__main__':
    unittest.main()
