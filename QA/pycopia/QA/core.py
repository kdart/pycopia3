#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.


"""Provides base classes for test cases, suites, and use cases.

This module defines a TestCase class, which is the base class for all test case
implementations. This class is not substantiated itself, but a subclass is
defined that overrides the `execute` method.

Your `execute` should call the ``pass`` or ``fail`` methods, as appropriate,
when the tested feature's test result is determined. If the result can't be
determined, then call the result is ``incomplete``, and that method should be
called.

You may also use the built-in ``assert*`` statements. There are also various
assertion methods that may be called.

If a test cannot be completed for some reason you may also raise a
'TestIncompleteError' exception.

The default result is ``incomplete``.

Usually, a set of test cases is collected in a TestSuite object, which is
constructed by a UseCase object (static object).  Therefore, the set of tests
run is dynamic, and can be adjusted depending on configuration options.  Test
cases are run in the order added to a test suite.


Example::

    class MyCase(UseCase):
        @staticmethod
        def get_suite(config):
            suite = TestSuite(name="MySuite")
            suite.add_test(MyTestSubclass)
            ...
            return suite

Then target the use case with a path to it in the runner. ::

    $ runtest testcases.subpackage.module.MyCase

Note that a UseCase is not instantiated. It's used as a holder for a the suite constructor and
allows for documentation.
"""

import sys
import os
import inspect
from datetime import datetime

from pycopia import debugger
from pycopia import dictlib
from pycopia import module
from pycopia import combinatorics
from pycopia.QA.signals import *
from pycopia.QA.exceptions import *

from pycopia.QA.constants import TestResult



class TestOptions:
    """A descriptor that forces OPTIONS to be class attributes that are not
    overridable by instances.
    """
    def __init__(self, initdict):
        # Default option value is empty iterable (evaluates false).
        self.OPTIONS = dictlib.AttrDictDefault(initdict, default=())

    def __get__(self, instance, owner):
        return self.OPTIONS

    # This is here to make instances not able to override options, but does
    # nothing else. Attempts to set testinstance.OPTIONS are simply ignored.
    def __set__(self, instance, value):
        pass


def insert_options(klass, **kwargs):
    if type(klass) is type and issubclass(klass, TestCase):
        if "OPTIONS" not in klass.__dict__:
            klass.OPTIONS = TestOptions(kwargs)
    else:
        raise ValueError("Need TestCase class.")


class TestCase:
    """Base class for all test cases.

    Subclass this to define a new test. Define the ``execute`` method in the subclass.  The test
    should test one specific thing. Optionally define the ``initialize`` and ``finalize`` methods.
    Those are run before, and after the ``execute`` method.
    """
    OPTIONS = TestOptions({})
    PREREQUISITES = []

    def __init__(self, config):
        cl = self.__class__
        self.test_name = "%s.%s" % (cl.__module__, cl.__name__)
        self.config = config
        #self._report = config.report
        self._debug = config.flags.DEBUG
        self._verbose = config.flags.VERBOSE

    @classmethod
    def set_test_options(cls):
        insert_options(cls)
        opts = cls.OPTIONS
        pl = []
        for prereq in cls.PREREQUISITES:
            if isinstance(prereq, str):
                pl.append(PreReq(prereq))
            elif type(prereq) is tuple:
                pl.append(PreReq(*prereq))
            else:
                raise ValueError("Bad prerequisite value.")
        opts.prerequisites = pl
        opts.bugid = None

    @property
    def prerequisites(self):
        return self.OPTIONS.prerequisites

    def run(self, *args, **kwargs):
        """Invoke the test.

        Handles the disposition exceptions, and optional debugging. Invokes the
        ``initialize`` and ``finalize`` methods.
        """
        test_arguments.send(self, arguments=repr_args(args, kwargs))
        self._initialize()
        # test elapsed time does not include initializer time.
        teststarttime = datetime.now()
        test_start.send(self, name=self.test_name, time=teststarttime)
        rv = None
        try:
            rv = self.execute(*args, **kwargs)
        except KeyboardInterrupt:
            if self._debug:
                ex, val, tb = sys.exc_info()
                debugger.post_mortem(tb, ex, val)
            self.incomplete("{}: aborted by user.".format(self.test_name))
            self._finalize()
            raise
        except TestFailError as errval:
            self.failed(str(errval))
        except TestIncompleteError as errval:
            self.incomplete(str(errval))
        # Test asserts and validation errors are based on this.
        except AssertionError as errval:
            self.failed("failed assertion: {}".format(errval))
        except TestSuiteAbort:
            raise # pass this one up to suite
        except debugger.DebuggerQuit: # set_trace "leaks" BdbQuit
            self.incomplete("{}: Debugger exit.".format(self.test_name))
        except:
            ex, val, tb = sys.exc_info()
            if self._debug:
                debugger.post_mortem(tb, ex, val)
                tb = None
            self.incomplete("{}: Exception: ({}: {})".format(self.test_name, ex, val))
        endtime = datetime.now()
        test_end.send(self, time=endtime)
        self._finalize()
        return rv

    def _initialize(self):
        try:
            self.initialize()
        except:
            ex, val, tb = sys.exc_info()
            self.diagnostic("%s (%s)" % (ex, val))
            if self._debug:
                debugger.post_mortem(tb, ex, val)
            raise TestSuiteAbort("Test initialization failed!")

    #Run user-defined `finalize()` and catch exceptions. If an exception
    #occurs in the finalize() method (which is supposed to clean up from
    #the test and leave the UUT in the same condition as when it was
    #entered) then abort the test suite.
    #Invokes the debugger if the debug flag is set.
    def _finalize(self):
        try:
            self.finalize()
        except:
            ex, val, tb = sys.exc_info()
            self.diagnostic("%s (%s)" % (ex, val))
            if self._debug:
                debugger.post_mortem(tb, ex, val)
            raise TestSuiteAbort("Test finalize failed!")

    # utility methods - methods that are common to nearly all tests.

    def get_filename(self, basename=None, ext="log"):
        """Create a log file name.

        Return a standardized log file name with a timestamp that should be
        unique enough to not clash with other tests, and also able to correlate
        it later to the test report via the time stamp. The path points to the
        resultsdir location.
        """
        filename = "%s-%s.%s" % (basename or self.test_name.replace(".", "_"),
                self.startime, ext)
        return os.path.join(self.config.resultsdir, filename)

    def open_log_file(self, basename=None, ext="log", mode="a+"):
        """Return a file object that you can write to in the results location."""
        fname = self.get_filename(basename, ext)
        return open(fname, mode)

    def run_subtest(self, _testclass, *args, **kwargs):
        """Invoke another TestCase class in the same environment as this one.

        Runs another TestCase subclass with the given arguments passed to the
        `execute()`.
        """
        inst = _testclass(self.config)
        return inst(*args, **kwargs)

    def debug_here(self):
        """Enter The Debugger.
        """
        debugger.set_trace(start=2)

    ### the overrideable methods follow ###
    def initialize(self):
        """Hook method to initialize a test.

        Override if necessary. This establishes the pre-conditions of the test.
        """
        pass

    def finalize(self):
        """Hook method when finalizing a test.

        Override if necessary. Used to clean up any state in UUT.

        """
        pass

    def execute(self, *args, **kw):
        """The primary test method. You must override this in a subclass.

        This method should call one, and only one, of the methods ``passed``,
        ``failed``, or ``incomplete``.
        """
        return self.incomplete(
                'you must define a method named "execute" in your subclass.')

    # result reporting methods
    def passed(self, msg="Passed"):
        """Call this and return if the execute() determines the test case passed.

        Only invoke this method if it is positively determined that the test case passed.
        """
        test_passed.send(self, message=msg)

    def failed(self, msg="Failed"):
        """Call this and return if the execute() method determines the test case failed.

        Only call this if your test implementation in the execute is positively
        sure that it does not meet the criteria. Other kinds of errors should
        return ``incomplete``. A diagnostic message should also be sent.

        If a bug is associated with this test case the result is converted into
        and EXPECTED_FAIL result.
        """
        if self.OPTIONS.bugid:
            test_diagnostic.send(self,
                message="This failure was expected. see bug: {}.".format(self.OPTIONS.bugid))
            test_expected_failure.send(self, message=msg)
        else:
            test_failure.send(self, message=msg)

    def expectedfail(self, msg="Expected failure"):
        """Call this and return if the execute() failed but that was expected.

        This is used primarily for exploratory testing where you may have a
        sequence of parameterized tests where some are expected to fail past a
        certain threshold. In other words, the test fails because the
        parameters are out of spec.
        """
        test_expected_failure.send(self, message=msg)

    def incomplete(self, msg="Incomplete"):
        """Test could not complete.

        Call this and return if your test implementation determines that the
        test cannot be completed for whatever reason.
        """
        test_incomplete.send(self, message=msg)

    def abort(self, msg="Aborted"):
        """Abort the test suite.

        Some drastic error occurred, or some condition is not met, and the
        suite cannot continue. Raises the TestSuiteAbort exception.
        """
        test_abort.send(self, message=msg)
        raise TestSuiteAbort(msg)

    def info(self, msg):
        """Informational messages to report.
        """
        test_info.send(self, message=msg)

    def diagnostic(self, msg):
        """Emit a diagnostic message.

        Call this if a failed condition is detected, and you
        want to record in the report some pertinent diagnostic information.
        """
        test_diagnostic.send(self, message=msg)

    def manual(self):
        """Perform a purely manual test according to the instructions in the document string.

        This allows manual tests to be mixed with automated tests.
        """
        UI = self.config.UI
        UI.print(self.test_name)
        UI.write(self.__class__.__doc__)
        UI.print("\nPlease perform this test according to the instructions above.")
        completed = UI.yes_no("%IWas it completed%N?")
        if completed:
            passed = UI.yes_no("Did it pass?")
            msg = UI.user_input("%gComments%N? " if passed else "%rReason%N? ")
            if passed:
                return self.passed("OK, user reported passed. " + msg)
            else:
                if msg:
                    self.diagnostic(msg)
                return self.failed("User reported failure.")
        else:
            msg = UI.user_input("%YReason%N? ")
            return self.incomplete("Could not perform test. " + msg)

    # assertion methods make it convenient to check conditions. These names
    # match those in the standard `unittest` module for the benefit of those
    # people using that module.
    def assertPassed(self, arg, msg=None):
        """Assert a sub-test run by the `run_subtest()` method passed.

        Used when invoking test objects as a unit.
        """
        if int(arg) != TestResult.PASSED:
            raise TestFailError(msg or "Did not pass test.")

    def assertFailed(self, arg, msg=None):
        """Assert a sub-test run by the `run_subtest()` method failed.

        Useful for "negative" tests.
        """
        if int(arg) not in (TestResult.FAILED, TestResult.EXPECTED_FAIL):
            raise TestFailError(msg or "Did not pass test.")

    def assertEqual(self, arg1, arg2, msg=None):
        """Asserts that the arguments are equal,

        Raises TestFailError if arguments are not equal. An optional message
        may be included that overrides the default message.
        """
        if arg1 != arg2:
            raise TestFailError(msg or "%s != %s" % (arg1, arg2))

    def assertNotEqual(self, arg1, arg2, msg=None):
        """Asserts that the arguments are not equal,

        Raises TestFailError if arguments are equal. An optional message
        may be included that overrides the default message.
        """
        if arg1 == arg2:
            raise TestFailError(msg or "%s == %s" % (arg1, arg2))

    def assertGreaterThan(self, arg1, arg2, msg=None):
        """Asserts that the first argument is greater than the second
        argument.
        """
        if not (arg1 > arg2):
            raise TestFailError(msg or "%s <= %s" % (arg1, arg2))

    def assertGreaterThanOrEqual(self, arg1, arg2, msg=None):
        """Asserts that the first argument is greater or equal to the second
        argument.
        """
        if not (arg1 >= arg2):
            raise TestFailError(msg or "%s < %s" % (arg1, arg2))

    def assertLessThan(self, arg1, arg2, msg=None):
        """Asserts that the first argument is less than the second
        argument.
        """
        if not (arg1 < arg2):
            raise TestFailError(msg or "%s >= %s" % (arg1, arg2))

    def assertLessThanOrEqual(self, arg1, arg2, msg=None):
        """Asserts that the first argument is less than or equal to the second
        argument.
        """
        if not (arg1 <= arg2):
            raise TestFailError(msg or "%s > %s" % (arg1, arg2))

    def assertTrue(self, arg, msg=None):
        """Asserts that the argument evaluates to True by Python.

        Raises TestFailError if argument is not True according to Python truth
        testing rules.
        """
        if not arg:
            raise TestFailError(msg or "%s not true." % (arg,))

    def assertFalse(self, arg, msg=None):
        """Asserts that the argument evaluates to False by Python.

        Raises TestFailError if argument is not False according to Python truth
        testing rules.
        """
        if arg:
            raise TestFailError(msg or "%s not false." % (arg,))

    def assertApproximatelyEqual(self, arg1, arg2, fudge=None, msg=None):
        """Asserts that the numeric arguments are approximately equal.

        Raises TestFailError if the second argument is outside a tolerance
        range (defined by the "fudge factor").    The default is 5% of the first
        argument.
        """
        if fudge is None:
            fudge = arg1*0.05
        if abs(arg1-arg2) > fudge:
            raise TestFailError(msg or "%s and %s not within %s units of each other." % \
                        (arg1, arg2, fudge))

    def assertRaises(self, exception, method, args=None, kwargs=None, msg=None):
        """Assert that a method and the given args will raise the given
        exception.

        Args:
            exception: The exception class the method should raise.
            method:    the method to call with the given arguments.
            args: a tuple of positional arguments.
            kwargs: a dictionary of keyword arguments
            msg: optional message string to be used if assertion fails.
        """
        args = args or ()
        kwargs = kwargs or {}
        try:
            method(*args, **kwargs)
        except exception:
            return
        # it might raise another exception, which is marked INCOMPLETE
        raise TestFailError(msg or "%r did not raise %r." % (method, exception))

    @classmethod
    def open_data_file(cls, fname):
        """Open a data file located in the same directory as the test case
        implmentation.
        """
        fullname = os.path.join(
                    os.path.dirname(sys.modules[cls.__module__].__file__), fname)
        return open(fullname)



# --------------------

class PreReq:
    """A holder for test prerequisite.

    Used to hold the definition of a prerequisite test. A prerequisite is a
    Test implementation class plus any arguments it may be called with.
    No arguments means ANY arguments.
    """
    def __init__(self, implementation, args=None, kwargs=None):
        self.implementation = str(implementation)
        self.args = args or ()
        self.kwargs = kwargs or {}

    def __repr__(self):
        return "%s(%r, args=%r, kwargs=%r)" % \
                (self.__class__.__name__, self.implementation,
                        self.args, self.kwargs)

    def __str__(self):
        return repr_test(self.implementation, self.args, self.kwargs)


class TestEntry:
    """Helper class to run a TestCase with arguments at some later time.

    Also helps manage prerequisite matching and track test results.
    """
    def __init__(self, inst, args=None, kwargs=None, autoadded=False):
        self.inst = inst
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.autoadded = autoadded # True if automatically added as a prerequisite.
        self.result = TestResult.NA
        test_passed.connect(self._passed, sender=inst)
        test_incomplete.connect(self._incomplete, sender=inst)
        test_failure.connect(self._failure, sender=inst)
        test_expected_failure.connect(self._expected_failure, sender=inst)

    def _passed(self, testcase, message=None):
        if self.result != TestResult.NA:
            raise TestImplementationError("Setting PASSED when result already set.")
        self.result = TestResult.PASSED

    def _incomplete(self, testcase, message=None):
        if self.result != TestResult.NA:
            raise TestImplementationError("Setting INCOMPLETE when result already set.")
        self.result = TestResult.INCOMPLETE

    def _failure(self, testcase, message=None):
        if self.result != TestResult.NA:
            raise TestImplementationError("Setting FAILED when result already set.")
        self.result = TestResult.FAILED

    def _expected_failure(self, testcase, message=None):
        if self.result != TestResult.NA:
            raise TestImplementationError("Setting EXPECTED_FAIL when result already set.")
        self.result = TestResult.EXPECTED_FAIL

    def run(self):
        """Invoke the test with its arguments. The config argument is passed
        when run directly from a TestRunner, but not from a TestSuite. It is
        ignored here.
        """
        self.inst.run(*self.args, **self.kwargs)
        return self.result

    def __eq__(self, other):
        return self.inst == other.inst

    def match_test(self, name, args, kwargs):
        """Test signature matcher.

        Determine if a test name and set of arguments matches this test.
        """
        return (name, args, kwargs) == \
                    (self.inst.test_name, self.args, self.kwargs)

    def match_prerequisite(self, prereq):
        """Does this test match the specified prerequisite?

        Returns True if this test matches the supplied PreReq object.
        """
        return (self.inst.test_name, self.args, self.kwargs) == \
                    (prereq.implementation, prereq.args, prereq.kwargs)

    @property
    def prerequisites(self):
        return self.inst.prerequisites

    @property
    def signature(self):
        """Return a unique identifier for this test entry."""
        try:
            return self._signature
        except AttributeError:
            arg_sig = repr((self.args, self.kwargs))
            self._signature = (id(self.inst.__class__), arg_sig)
            return self._signature

    @property
    def test_name(self):
        return self.inst.test_name

    def __repr__(self):
        return repr_test(self.inst.test_name, self.args, self.kwargs)

    def __str__(self):
        return "%s: %s" % (self.__repr__(), self.result)


class SuiteEntry:
    """Entry object that wraps other Suite objects.

    Used when sub-suites are run as test cases.
    """
    def __init__(self, suiteinst):
        self.inst = suiteinst

    def run(self):
        self.inst.run()


def PruneEnd(n, l):
    return l[:n]

class TestEntrySeries(TestEntry):
    """A single entry for a dynamic series of tests.

    Provides an efficient means to add many test case instances without
    having to actually instantiate a TestEntry at suite build time.
    """
    def __init__(self, testinstance, N, chooser, filt, args, kwargs):
        self.inst = testinstance
        self.args = args or ()
        self.kwargs = kwargs or {}
        self._sig = inspect.signature(testinstance.execute)
        self.result = TestResult.NA # aggregate result
        chooser = chooser or PruneEnd
        arglist = []
        if args:
            arglist.extend(args)
        if kwargs:
            for name, default in self._sig.kwarguments:
                try:
                    val = kwargs[name]
                except KeyError:
                    pass
                else:
                    arglist.append(val)
        self._counter = combinatorics.ListCounter(combinatorics.prune(N, arglist, chooser))
        if filt:
            assert callable(filt)
            self._filter = filt
        else:
            self._filter = lambda *args, **kwargs: True

    @property
    def test_name(self):
        return self.inst.test_name

    def match_prerequisite(self, prereq):
        """Does this test match the specified prerequisite?

        Returns True if this test name matches the supplied PreReq object.
        Only the name is checked for series tests, since the arguments may vary.
        """
        return self.inst.test_name == prereq.implementation

    def run(self, config=None):
        resultset = {TestResult.PASSED:0, TestResult.FAILED:0,
                TestResult.EXPECTED_FAIL:0, TestResult.INCOMPLETE:0}
        for argset in self._counter:
            kwargs = self._sig.get_keyword_arguments(argset)
            # kwargs also contains non-keyword args, but python maps them to
            # positional args anyway.
            if self._filter(**kwargs):
                entry = TestEntry(self.inst, (), kwargs)
                entryresult = entry.run()
                resultset[entryresult] += 1
        if resultset[TestResult.FAILED] > 0:
            self.result = TestResult.FAILED
        elif resultset[TestResult.INCOMPLETE] > 0:
            self.result = TestResult.INCOMPLETE
        elif resultset[TestResult.PASSED] > 0:
            self.result = TestResult.PASSED
        return self.result


def repr_test(name, args, kwargs):
    """Produce repr form of test case signature.

    Returns a TestCase instantiation plus arguments as text (repr).
    """
    return "%s()(%s)" % (name, repr_args(args, kwargs))

def repr_args(args, kwargs):
    """Stringify a set of arguments.

    Arguments:
        args: tuple of arguments as a function would see it.
        kwargs: dictionary of keyword arguments as a function would see it.
    Returns:
        String as you would write it in a script.
    """
    args_s = (("%s, " if kwargs else "%s") % ", ".join(map(repr, args))) if args else ""
    kws = ", ".join(["%s=%r" % (it[0], it[1]) for it in list(kwargs.items())])
    return "%s%s" % (args_s, kws)


def parse_args(arguments):
    """Take a string of arguments and keyword arguments and convert back to
    objects.
    """
    # Try a possibly icky method of constructing a temporary function string
    # and exec it (leverage Python parser and argument handling).
    ANY = None # To allow "ANY" keyword in prereq spec.
    def _ArgGetter(*args, **kwargs):
        return args, kwargs
    funcstr = "args, kwargs = _ArgGetter(%s)\n" % arguments
    exec(funcstr, locals())
    return args, kwargs # set by exec call


class TestSuite:
    """A TestCase holder and runner.

    A TestSuite contains a set of test cases (subclasses of TestCase class) that
    are run sequentially, in the order added. It monitors abort status of
    each test, and aborts the suite if required.

    To run it, create a TestSuite object (or a subclass with some methods overridden),
    Add tests with the `add_test()` method, and then call the instance's run method.
    The 'initialize()' method will be run with the arguments given when run.

    The test result if a suite is the aggregate of contained tests. If all tests
    pass the suite is passed also. If any fail, the suite is failed. If any are
    incomplete the suite is incomplete.
    """
    def __init__(self, cf, nested=0, name=None):
        self.config = cf
        self._debug = cf.flags.DEBUG
        self._tests = []
        self._testset = set()
        self._multitestset = set()
        self._nested = nested
        cl = self.__class__
        self.test_name = name or "%s.%s" % (cl.__module__, cl.__name__)
        self.result = TestResult.NA

    def __iter__(self):
        return iter(self._tests)

    def _add_with_prereq(self, entry, _auto=False):
        if self._debug < 3:
            for prereq in entry.inst.OPTIONS.prerequisites:
                impl = prereq.implementation
                # If only a class name is given, assume it refers to a class
                # in the same module as the defining test, and convert to full
                # path using that module.
                if "." not in impl:
                    impl = sys.modules[entry.inst.__class__.__module__].__name__ + "." + impl
                    prereq.implementation = impl
                pretestclass = module.get_object(impl)
                pretestclass.set_test_options()
                preentry = TestEntry(pretestclass(self.config), prereq.args, prereq.kwargs, True)
                presig, argsig = preentry.signature
                if presig not in self._multitestset:
                    self._add_with_prereq(preentry, True)
        testcaseid = entry.signature
        if not _auto:
            self._tests.append(entry)
        elif testcaseid not in self._testset:
                self._tests.append(entry)
        self._testset.add(testcaseid)


    def add_test(self, _testclass, *args, **kwargs):
        """Add a TestCase subclass and its arguments to the suite.

    Appends a test object in this suite. The test's ``execute`` will be
    called (at the appropriate time) with the arguments supplied here. If
    the test case has a prerequisite defined it is checked for existence in
    the suite, and an exception is raised if it is not found.
    """
        if isinstance(_testclass, str):
            _testclass = module.get_class(_testclass)
        _testclass.set_test_options()
        testinstance = _testclass(self.config)
        entry = TestEntry(testinstance, args, kwargs, False)
        self._add_with_prereq(entry)

    def add_tests(self, _testclasslist, *args, **kwargs):
        """Add a list of tests at once.

        Similar to add_test method, but adds all test case classes found in the
        given list.  Arguments are common to all tests.
        If object is a tuple it should be a (testclass, tuple, dictionary) of
        positional and keyword arguments.
        """
        assert isinstance(_testclasslist, list)
        for testclass in _testclasslist:
            if type(testclass) is tuple:
                self.add_test(*testclass)
            else:
                self.add_test(testclass, *args, **kwargs)

    def add_test_series(self, _testclass, N=100, chooser=None, filter=None,
                                        args=None, kwargs=None):
        """Add a TestCase case as a series.

        The arguments must be lists of possible values for each parameter. The
        args and kwargs arguments are lists that are combined in all possible
        combinations, except pruned to N values. The pruning policy can be
        adjusted by the chooser callback, and the N value itself.

        Args:
            testclass (class): the TestCase class object (subclass of core.TestCase).

            N (integer): Maximum iterations to take from resulting set. Default
                    is 100 just to be safe.

            chooser (callable): callable that takes one number and a list
                    argument, returns a list of the specified (N) length.
                    Default is to chop off the top end of the list.

            filter (callable): callable that takes a set of arguments with the
                    same semantics as the TestCase.execute() method and returns True or
                    False to indicate if that combination should be included in the
                    test. You might want to set a large N if you use this.

            args (tuple): tuple of positional arguments, each argument is a list.
                                        example: args=([1,2,3], [4,5]) maps to positional
                                        argumnts of execute() method of TestCase class.

            kwargs (dict): Dictionary of keyword arguments, with list of values
                    as value.
                                        example: kwargs={"arg1":["a", "b", "c"]}
                                        maps to keyword arguments of execute() method of TestCase
                                        class.
        """
        if isinstance(_testclass, str):
            _testclass = module.get_class(_testclass)
        _testclass.set_test_options()
        testinstance = _testclass(self.config)
        try:
            entry = TestEntrySeries(testinstance, N, chooser, filter, args, kwargs)
        except ValueError as err: # ListCounter raises this if there is an empty list.
            self.info("addTestSeries Error: %s. Not adding %s as series." % (
                    err, _testclass.__name__))
        else:
            # series tests don't get auto-added (can't know what all the args
            # are, and even so the set could be large.)
            mysig, myargsig = entry.signature
            self._multitestset.add(mysig) # only add by id.
            self._add_with_prereq(entry)

    def add_suite(self, suite, test_name=None):
        """Add an entire suite of tests to this suite.

    Appends an embedded test suite in this suite. This is called a sub-suite
    and is treated as a single test by this containing suite.
    """
        if isinstance(suite, str):
            suite = module.get_class(suite)
        if type(suite) is type(TestCase): # class type
            suite = suite(self.config, 1)
        else:
            suite.config = self.config
            suite._nested = 1
        self._tests.append(SuiteEntry(suite))
        # sub-tests need unique names
        if test_name:
            suite.test_name = test_name
        else:
            # Name plus index into suite list.
            suite.test_name = "%s-%s" % (suite.test_name, len(self._tests)-1)
        return suite

    def add(self, klass, *args, **kwargs):
        """Add a Suite or a TestCase to this TestSuite.

    Most general method to add test case classes or other test suites.
    """
        if type(klass) is type:
            if issubclass(klass, TestCase):
                self.add_test(klass, *args, **kwargs)
            elif issubclass(klass, TestSuite):
                self.add_suite(klass, *args, **kwargs)
            else:
                raise ValueError("TestSuite.add: invalid class type.")
        else:
            raise ValueError("TestSuite.add: need a class type.")

    def get_test_entries(self, name, *args, **kwargs):
        """Get a list of test entries that matches the signature.

        Return a list of TestCase entries that match the name and calling
        arguments.
        """
        for entry in self._tests:
            if entry.matches(name, args, kwargs):
                yield entry

    def add_arguments(self, name, args, kwargs):
        """Add calling arguments to an existing test entry that has no
        arguments.
        """
        for entry in self.get_test_entries(name):
            entry.add_arguments(args, kwargs)

    @property
    def prerequisites(self):
        """Get the list of prerequisites.

        This is here for polymorhism with TestCase objects. Always return empty list.
        """
        return ()

    def run(self, *args, **kwargs):
        """Invoke the test suite.

        Calling the instance is the primary way to invoke a suite of tests.
        Any supplied parameters are passed onto the suite's initialize()
        method.

        It will then run all TestEntry, report on interrupts, and check for
        abort conditions. It will also skip tests whose prerequisites did not
        pass. If the debug level is 2 or more then the tests are not skipped.
        """
        self._initialize(*args, **kwargs)
        starttime = datetime.now()
        suite_start.send(self, time=starttime)
        self._run_tests()
        endtime = datetime.now()
        suite_end.send(self, time=endtime)
        self._finalize()
        return self.result

    def _initialize(self, *args, **kwargs):
        try:
            self.initialize(*args, **kwargs)
        except KeyboardInterrupt:
            self.info("Suite aborted by user in initialize().")
            raise TestSuiteAbort("Interrupted in suite initialize.")
        except:
            ex, val, tb = sys.exc_info()
            if self._debug:
                ex, val, tb = sys.exc_info()
                debugger.post_mortem(tb, ex, val)
            self.info("Suite failed to initialize: %s (%s)" % (ex, val))
            raise TestSuiteAbort(val)

    def check_prerequisites(self, currententry, upto):
        """Verify that the prerequisite test passed.

        Verify any prerequisites are met at run time.
        """
        for prereq in currententry.prerequisites:
            for entry in self._tests[:upto]:
                if entry.match_prerequisite(prereq):
                    if entry.result.is_passed():
                        continue
                    else:
                        tc = currententry.inst.test_name
                        test_start.send(tc, name=tc.test_name, time=datetime.now())
                        test_diagnostic.send(tc, message="Prerequisite: {}".format(prereq))
                        test_incomplete.send(tc, message="Prerequisite did not pass.")
                        test_end.send(tc, time=datetime.now())
                        currententry.result = TestResult.INCOMPLETE
                        return False
        return True # No prerequisite, or prereq did pass.

    def _run_tests(self):
        for i, entry in enumerate(self._tests):
            if self._debug < 2 and not self.check_prerequisites(entry, i):
                continue
            try:
                entry.run()
            except KeyboardInterrupt:
                if self._nested:
                    raise TestSuiteAbort("Sub-suite aborted by user.")
                else:
                    if self.config.UI.yes_no("Test interrupted. Abort suite?"):
                        self.info("Test suite aborted by user.")
                        break
            except TestSuiteAbort as err:
                self.info("Suite aborted by test {} ({}).".format(entry.test_name, err))
                break

    def _finalize(self):
        try:
            self.finalize()
        except KeyboardInterrupt:
            if self._nested:
                raise TestSuiteAbort(
                        "Suite {!r} aborted by user in finalize().".format(self.test_name))
            else:
                self.info("Suite aborted by user in finalize().")
        except:
            ex, val, tb = sys.exc_info()
            if self._debug:
                print() # ensure debugger prompts starts on new line.
                debugger.post_mortem(tb, ex, val)
            self.info("Suite failed to finalize: {} ({})".format(ex, val))
            if self._nested:
                raise TestSuiteAbort(
                        "subordinate suite {!r} failed to finalize.".format(self.test_name))
        resultset = {TestResult.PASSED:0, TestResult.FAILED:0,
                TestResult.EXPECTED_FAIL:0, TestResult.INCOMPLETE:0,
                TestResult.NA:0}
        # Aggregate result for suite.
        for entry in self._tests:
            resultset[entry.result] += 1
        if resultset[TestResult.FAILED] > 0:
            self.result = TestResult.FAILED
        elif resultset[TestResult.INCOMPLETE] > 0:
            self.result = TestResult.INCOMPLETE
        elif resultset[TestResult.PASSED] > 0:
            self.result = TestResult.PASSED

    def __str__(self):
        s = ["Tests in suite:"]
        s.extend(list(map(str, self._tests)))
        return "\n".join(s)

    def info(self, msg):
        """Send info message for a this suite.
        """
        suite_info.send(self, message=msg)

    ### overrideable interface. ###
    def initialize(self, *args, **kwargs):
        """initialize phase handler for suite-level initialization.

        Override this if you need to do some initialization just before the
        suite is run. This is called with the arguments given to the TestSuite
        object when it was called.
        """
        pass

    def finalize(self):
        """Run the finalize phase for suite level.

        Aborts the suite on error or interrupt. If this is a sub-suite then
        TestSuiteAbort is raised so that the top-level suite can handle it.

        Override this if you need to do some additional clean-up after the suite is run.
        """
        pass

Test = TestCase # backwards compatibility

class UseCase:
    """UseCase holds a TesetSuite constructor.

    Subclass this in your test module and define the ``get_suite`` static method.

    Be sure to add some documentation to your subclass to describe the use case.

    This allows for dynamic suite construction. Suites may have different sets
    of tests depending on the runtime configuration.


    """
    @staticmethod
    def get_suite(config):
        return TestSuite(config, name="EmptySuite")

    @classmethod
    def run(cls, config):
        suite = cls.get_suite(config)
        suite.run()
        return suite.result

