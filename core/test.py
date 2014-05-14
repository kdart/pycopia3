#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 1999-2006  Keith Dart <keith@kdart.com>
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


import os
import time

import unittest

from pycopia import asyncio
from pycopia import basicconfig
from pycopia import benchmarks
from pycopia import cliutils
from pycopia import combinatorics
from pycopia import daemonize
from pycopia import environ
#from pycopia import ezmail
from pycopia import fsm
from pycopia import guid
from pycopia import ipv4
from pycopia import logfile
from pycopia import makepassword
from pycopia import md5lib
from pycopia import methodholder
from pycopia import netstring
from pycopia import scheduler
from pycopia import smtp_envelope
from pycopia import sourcegen
from pycopia import shparser
from pycopia import table
from pycopia import texttools
from pycopia import passwd
from pycopia import re_inverse


from pycopia.inet import ABNF
from pycopia.inet import fcgi
from pycopia.inet import httputils
from pycopia.inet import rfc2822
from pycopia.inet import telnet

from pycopia.ISO import iso3166
from pycopia.ISO import iso639a

import pycopia.OS
#import pycopia.OS.sequencer


class CoreTests(unittest.TestCase):


    def test_ipv4(self):
        """basic test of ipv4 module."""

        r1 = ipv4.IPRange("172.22.1.11/24", "172.22.1.21/24")
        r2 = ipv4.IPRange("172.22.1.21/24", "172.22.1.11/24")
        r3 = ipv4.IPRange("172.22.1.55/24", "172.22.1.55/24")

        l1 = list(r1)
        l2 = list(r2)
        print(l1)
        print(l1 == l2)
        print(r3, list(r3))

        ip = ipv4.IPv4("172.22.4.1/24")
        self.assertEqual(ip.mask, 0b11111111111111111111111100000000)
        print(ip.address)
        ip.address = "172.22.4.2/24"
        print(ip.address)
        ip.address = -1407843325
        print(ip.CIDR)

        ip = ipv4.IPv4("1.1.1.1/30")
        print(len(ip))
        print(len(ipv4.IPv4("1.1.1.1/29")))
        print(len(ipv4.IPv4("1.1.1.1/28")))
        print(len(ipv4.IPv4("1.1.1.1/24")))
        for each_ip in ip:
            print(each_ip)
        self.assertEqual(ip.mask, 0b11111111111111111111111111111100)
        self.assertEqual(ip.address, 0x01010101)

    def test_passwd(argv):
        pwent = passwd.getpwself()
        print(repr(pwent))
        print(str(pwent))
        print(int(pwent))
        print(pwent.name)
        print(pwent.home)
        print(pwent.uid)
        print(pwent[3])

    def test_shparser(self):
        argv = None
        def _check_argv(argv):
            self.assertEqual(argv[0], "echo")
            self.assertEqual(argv[1], "-q")
            self.assertEqual(argv[3], "")
            self.assertEqual(argv[9], "bogus one")
            self.assertEqual(argv[10], argv[11])
        sh = shparser.ShellParser(_check_argv)
        rv = sh.feedline('echo -q -N "" -t tparm -b 1024 -f "bogus one" $PATH ${PATH}')

    def test_re_inverse(self):
        import sre_parse
        RE = r'(firstleft|)somestring(\s.*|) \S(a|b) [fgh]+ {2,3}R(\S)'
        print(sre_parse.parse(RE))
        for i in range(20):
            ms = re_inverse.make_match_string(RE)
        for i in range(20):
            ms = re_inverse.make_nonmatch_string(RE)

    def XXXtest_sequencer(self):
        counters = [0, 0, 0, 0, 0]
        starttimes = [None, None, None, None, None]
        def _test_job(counters):
            print ("test job 1")
            counters[0] += 1
        def _test_job2(counters):
            print ("test job 2")
            counters[1] += 1
        def _test_delay_job(counters, starttimes):
            if counters[2] == 0:
                starttimes[2] = time.time()
            print ("test delay job")
            counters[2] += 1
        def _test_delay_job2(counters, starttimes):
            if counters[3] == 0:
                starttimes[3] = time.time()
            print ("test delay job 2 at", time.time())
            counters[3] += 1
        def _test_oneshot(counters, starttimes):
            thetime = time.time()
            counters[4] += 1
            starttimes[4] = thetime
            print ("test oneshot at", thetime)

        s = pycopia.OS.sequencer.Sequencer()
        start = time.time()
        s.add_task(_test_job, 2.0, duration=20.0, callback_args=(counters,))
        s.add_task(_test_job2, 3.0, duration=30.0, callback_args=(counters,))
        s.add_task(_test_delay_job, 3.1, delay=35, duration=18.0, callback_args=(counters,starttimes))
        s.add_task(_test_delay_job2, 2.0, delay=55, duration=3.0, callback_args=(counters,starttimes))
        s.add_task(_test_oneshot, 0.0, delay=15, callback_args=(counters,starttimes))
        s.run()
        s.close()
        endtime = time.time()
        self.assertAlmostEqual(endtime-start, 58.0, places=2) # job2 delay plus duration (max time)
        self.assertAlmostEqual(starttimes[2] - start, 35.0, places=2) # delay_job start delay
        self.assertAlmostEqual(starttimes[3] - start, 55.0, places=2) # delay_job2 start delay
        self.assertAlmostEqual(endtime - starttimes[3], 3.0, places=2) # test_delay_job2
        self.assertAlmostEqual(starttimes[4] - start, 15.0, places=2) # oneshot delay
        self.assertEqual(counters[0], 10)
        self.assertEqual(counters[1], 10)
        self.assertEqual(counters[2], 6)
        self.assertEqual(counters[3], 2)
        self.assertEqual(counters[4], 1)




if __name__ == '__main__':
    unittest.main()
