#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
# License: LGPL

"""
Module commandtest runs external commands, provides inputs, and checks outputs.

"""

from pycopia import proctools


class TestCondition:
    """TestCondition holds test data for use by the test_command function.
Attributes are:

    - cmdline
    - stdin
    - expectedout
    - expectederr
    - expectedexit
    - environ
    """
    __slots__ = ('cmdline', 'stdin', 'expectedout',
                'expectederr', 'expectedexit', 'environ')
    def __init__(self, cmdline=None, environ=None, stdin=None, expectedout=None, expectederr=None, expectedexit=0):
        self.cmdline = cmdline
        self.stdin = stdin # what to write to programs stdin
        self.expectedout=expectedout # what is expected to come out
        self.expectederr=expectederr
        self.expectedexit=expectedexit # expected errorlevel value
        self.environ = environ # environment program will run with.

    def __repr__(self):
        return "%s(%r, %r, %r, %r, %r, %r)" % (self.__class__.__name__,
            self.cmdline, self.environ, self.stdin, self.expectedout,
            self.expectederr, self.expectedexit)


class CommandTestMixin:
    """Mixin class for QA.core.TestCase subclasses that runs and verifies subprocess output.
    """

    def test_command(self, testcondition):
        cmdline = testcondition.cmdline
        stdin = testcondition.stdin
        expectedout = testcondition.expectedout
        expectederr = testcondition.expectederr
        expectedexit = testcondition.expectedexit
        environ = testcondition.environ

        if expectederr:
            mergeerr = 0
        else:
            mergeerr = 1
        self.info("running: %s" % cmdline)
        p = proctools.spawnpipe(cmdline, env=environ, merge=mergeerr)
        if stdin:
            p.write(stdin)
        if expectedout:
            output = p.read()
        if expectederr:
            errors = p.readerr()
        p.wait()
        es = p.exitstatus
        if int(es) != expectedexit:
            self.failed("bad exit value: expected %d, got %d" % (expectedexit, int(es)))

        if expectedout and (output != expectedout):
            self.failed("bad output: %r" % (output))

        if expectederr and (errors != expectederr):
            self.failed("bad error output: %r" % (errors))

        self.passed("no errors detected.")

