#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import unittest

from pycopia import proctools
from pycopia import crontab
from pycopia import expect
from pycopia import sshlib
from pycopia import sudo

def _sub_function():
    from pycopia import scheduler
    scheduler.sleep(5)
    return None

def _co_function():
    import sys
    from pycopia import scheduler
    sys.stdout.write("hello from co_function\n")
    scheduler.sleep(5)
    return None

class ProcessTests(unittest.TestCase):
    def setUp(self):
        pass

    def test_spawnpipe(self):
        ls = proctools.spawnpipe("ls /usr/bin")
        files = ls.read()
        self.assertTrue(files)
        self.assertFalse(ls.readerr())
        ls.close()
        es = ls.wait()
        self.assertTrue(es)

    def test_lserror(self):
        ls = proctools.spawnpipe("ls /usr/binxx", merge=0)
        out = ls.read()
        errout = ls.readerr()
        self.assertFalse(bool(out))
        self.assertTrue(bool(errout))
        ls.close()
        ls.wait()
        es = ls.stat()
        self.assertFalse(es)

    def test_readaline(self):
        lspm = proctools.spawnpipe("ls /bin")
        lines = lspm.readlines()
        self.assertTrue(lines)
        lspm.close()
        es = lspm.exitstatus
        self.assertTrue(es)

#    def test_pipeline(self):
#        ptest = proctools.spawnpipe("cat /etc/hosts | sort")
#        hosts = ptest.read()
#        self.assertTrue(bool(hosts))
#        self.assertFalse(bool(ptest.readerr()))
#        ptest.close()
#        es = ptest.stat()
#        self.assertTrue(es)

    def test_subprocess(self):
        sub = proctools.subprocess(_sub_function)
        es = sub.wait()
        self.assertTrue(es)

    def test_coprocess(self):
        sub = proctools.coprocess(_co_function)
        line = sub.readline()
        es = sub.wait()
        self.assertTrue(es)

    def XXXtest_sudo(self):
        pw = sudo.getpw()
        proc = sudo.sudo("/bin/ifconfig -a", password=pw)
        print(proc.read())
        print(repr(proc.readerr()))
        proc.wait()
        sudo.sudo_reset()


if __name__ == '__main__':
    unittest.main()




