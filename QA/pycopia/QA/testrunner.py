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

"""Top level test runner.

This module provides the primary test runner for the automation framework.

Modules that define a "run" function:
    A base TestCase is instantiated. The methods are inserted into the module
    namespace.
    The objects "config" and "environment" are inserted into to module
    namespace.
    The *execute* function is called with no arguments.

    Note that a UseCase class typically defines a *get_suite* method that it's
    own run method will call. the get_suite should construct a TestSuite
    instance.

Class object that is a TestCase:
    Instantiate a TestSuite and add the test case to it. Then instantiate and
    run the TestSuite.
"""

import os
import sys
from datetime import datetime

from pycopia import logging
from pycopia import reports
from pycopia import debugger

from . import core
from . import config
from . import environment
from .exceptions import TestRunnerError, ReportFindError
from .signals import (run_start, run_end, report_url,
                      run_comment, run_arguments, dut_version)
from .constants import TestResult

ModuleType = type(os)


# Test case methods inserted into plain modules for plain module test cases.
_EXPORTED_METHODS = ['abort', 'assertApproximatelyEqual', 'assertEqual',
                     'assertFailed', 'assertFalse', 'assertGreaterThan',
                     'assertGreaterThanOrEqual', 'assertLessThan',
                     'assertLessThanOrEqual', 'assertNotEqual', 'assertPassed',
                     'assertRaises', 'assertTrue', 'diagnostic',
                     'expectedfail', 'failed', 'get_filename', 'incomplete',
                     'info', 'open_data_file', 'open_log_file', 'passed', ]


class TestRunner:
    """Runs test objects.

    Handled running objects, initializing reports,
    running tests and cleaning up afterwards.
    """
    def __init__(self, storageurl=None):
        self.config = cf = config.get_config(storageurl=storageurl)
        cf.arguments = []
        if cf.flags.DEBUG:
            logging.loglevel_debug()
        else:
            logging.loglevel_info()

    def run(self, objects, ui):
        """Main entry to run a list of runnable objects."""
        self._ui = ui
        self.initialize()
        rv = self.run_objects(objects)
        self.finalize()
        return rv

    def run_objects(self, objects):
        """Invoke the `run` method on a list of mixed runnable objects.

        Arguments:
            objects:
                A list of runnable objects. A runnable object is basically
                something that has a callable named "run" that takes a
                configuration, environment, and UI object as a parameter.

                A special module with an "execute" function can also be run.

        May raise TestRunnerError if an object is not runnable by this test
        runner.

        Bare TestCase classes are grouped together and run in a temporary
        TestSuite.
        """
        rv = TestResult.INCOMPLETE
        results = []
        testcases = []
        for obj in objects:
            objecttype = type(obj)
            if objecttype is type:
                if issubclass(obj, core.TestCase):
                    testcases.append(obj)
                if issubclass(obj, core.UseCase):
                    rv = obj.run(self.config, self.environment, self._ui)
            elif isinstance(obj, core.TestSuite):
                obj.run()
                rv = obj.result
            elif objecttype is ModuleType:
                if hasattr(obj, "execute"):
                    rv = self._run_module_hack(obj)
                elif hasattr(obj, "run"):
                    rv = self._run_module(obj)
            else:
                logging.warn("{!r} is not a runnable object.".format(obj))
            results.append(rv)
        # Run any accumulated bare test classes.
        if testcases:
            if len(testcases) > 1:
                rv = self.run_tests(testcases)
            else:
                rv = self.run_test(testcases[0])
            results.append(rv)
        return _aggregate_returned_results(results)

    def _run_module_hack(self, module_with_exec):
        tcinst = core.TestCase(self.config, self.environment, self._ui)
        tcinst.set_test_options()
        tcinst.test_name = module_with_exec.__name__
        # Pull out essential functions.
        execute = getattr(module_with_exec, "execute")
        initialize = getattr(module_with_exec, "initialize", None)
        finalize = getattr(module_with_exec, "finalize", None)
        # Make functions bound methods of temporary TestCase instance.
        MethodType = type(tcinst.execute)
        def wrap_execute(s):
            return execute()
        setattr(tcinst, "execute", MethodType(wrap_execute, tcinst))
        if initialize is not None:
            def wrap_initialize(s):
                return initialize()
            setattr(tcinst, "initialize", MethodType(wrap_initialize, tcinst))
        if finalize is not None:
            def wrap_finalize(s):
                return finalize()
            setattr(tcinst, "finalize", MethodType(wrap_finalize, tcinst))
        # Put TestCase instance methods into module namespace.
        # This enables execute function to call disposition methods as globals.
        for name in _EXPORTED_METHODS:
            value = getattr(tcinst, name)
            setattr(module_with_exec, name, value)
        module_with_exec.config = self.config
        module_with_exec.environment = self.environment
        module_with_exec.UI = self._ui
        module_with_exec.print = tcinst.info
        module_with_exec.input = self._ui.user_input
        # Run inside a TestEntry, which handles result reporting.
        try:
            entry = core.TestEntry(tcinst)
            rv = entry.run()
        except:
            if self.config.flags.DEBUG:
                ex, val, tb = sys.exc_info()
                debugger.post_mortem(tb, ex, val)
            else:
                logging.exception_error(module_with_exec.__name__)
            rv = TestResult.INCOMPLETE
        # Clean up
        del module_with_exec.config
        del module_with_exec.environment
        del module_with_exec.UI
        del module_with_exec.print
        del module_with_exec.input
        for name in _EXPORTED_METHODS:
            delattr(module_with_exec, name)
        return rv

    def _run_module(self, module_with_run):
        try:
            rv = module_with_run.run(self.config, self.environment, self._ui)
        except:
            if self.config.flags.DEBUG:
                ex, val, tb = sys.exc_info()
                debugger.post_mortem(tb, ex, val)
            else:
                logging.exception_error(module_with_run.__name__)
            return TestResult.INCOMPLETE
        else:
            return rv

    def run_test(self, testclass, *args, **kwargs):
        """Run a test single test class with arguments.

        Runs a single test class with the provided arguments. Test class
        is placed in a temporary TestSuite.

        Arguments:
            testclass:
                A class that is a subclass of core.Test. Any extra arguments
                given are passed to the `execute()` method when it is invoked.

        Returns:
            The return value of the Test instance. Should be PASSED, FAILED,
            INCOMPLETE, or ABORT.
        """

        suite = core.TestSuite(self.config, self.environment, self._ui,
                               name="{}Suite".format(testclass.__name__))
        suite.add_test(testclass, *args, **kwargs)
        suite.run()
        return suite.result

    def run_tests(self, testclasses):
        """Run a list of test classes.

        Runs a list of test classes. Test classes are placed in a temporary
        TestSuite.

        Arguments:
            testclasses:
                A list of classes that are subclasses of core.Test.

        Returns:
            The return value of the temporary TestSuite instance.
        """

        suite = core.TestSuite(self.config, self.environment, self._ui,
                               name="RunTestsTempSuite")
        suite.add_tests(testclasses)
        suite.run()
        return suite.result

    def _create_results_dir(self):
        """Make results dir, don't worry if it already exists."""
        try:
            os.mkdir(self.config.resultsdir)
        except FileExistsError:
                pass

    def _set_report_url(self):
        cf = self.config
        baseurl = cf.get("baseurl")
        documentroot = cf.get("documentroot")
        resultsdir = cf.resultsdir
        if baseurl and documentroot:
            report_url.send(self, message="Artifact location.",
                            url=baseurl+resultsdir[len(documentroot):])
        else:
            report_url.send(self, message="Artifact file location.",
                            url="file://" + resultsdir)

    def initialize(self):
        """Perform any initialization needed by the test runner.

        Initializes report. Sends runner and header messages to the report.
        """
        cf = self.config
        self.environment = environment.get_environment(
            cf.get("environmentname", "default"))
        cf.username = os.environ["USER"]
        self.environment.owner = cf.username
        # used as the timestamp for output location.
        runnertimestamp = datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
        # set resultsdir to full path where test run artifacts are placed.
        cf.resultsdir = os.path.join(
            os.path.expandvars(cf.get("resultsdirbase", "/var/tmp")),
            "{}-{}".format(runnertimestamp, cf.username))
        try:
            rpt = reports.get_report(cf)
        except ReportFindError as err:
            self._ui.error(str(err))
            raise TestRunnerError("Cannot continue without report.")
        rpt.initialize(title=" ".join(cf.get("argv", ["unknown"])))
        cf.report = rpt
        run_start.send(self, timestamp=runnertimestamp)
        arguments = cf.get("arguments")
        # Report command line arguments, if any.
        if arguments:
            run_arguments.send(self, message=" ".join(arguments))
        # Report comment, if any.
        comment = cf.get("comment")
        if comment:
            run_comment.send(self, message=comment)
        # Report build here, if given.
        build = cf.get("build")
        if build:
            dut_version.send(self, version=build)
        self._create_results_dir()
        self._set_report_url()

    def finalize(self):
        """Perform any finalization needed by the test runner.
        Sends runner end messages to report. Finalizes report.
        """
        run_end.send(self)
        cf = self.config
        rpt = cf.report
        rpt.finalize()
        self.environment.clear()
        self.environment.owner = None
        del self.environment
        del cf["report"]
        # remove log/results directory if it's empty.
        st = os.stat(cf.resultsdir)
        if st.st_nlink == 2:
            os.rmdir(cf.resultsdir)


def _aggregate_returned_results(resultlist):
    resultset = {TestResult.PASSED: 0, TestResult.FAILED: 0,
                 TestResult.EXPECTED_FAIL: 0, TestResult.INCOMPLETE: 0,
                 TestResult.NA: 0, None: 0}
    for res in resultlist:
        resultset[res] += 1
    # Fail if any fail, else incomplete if any incomplete, pass if all pass.
    if resultset[TestResult.FAILED] > 0:
        return TestResult.FAILED
    elif resultset[TestResult.INCOMPLETE] > 0:
        return TestResult.INCOMPLETE
    elif resultset[None] > 0:
        return TestResult.NA
    elif resultset[TestResult.PASSED] > 0:
        return TestResult.PASSED
    else:
        return TestResult.INCOMPLETE
