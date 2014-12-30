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

Class objects that is not a TestSuite or TestCase:
    Instantiate the class with config and environment.
    call the instances *run* method with no arguments.

    Note that a UseCase class typically defines a *get_suite* method that it's
    own run method will call. the get_suite should construct a TestSuite
    instance.

Class object that is a TestCase:
    Instantiate a TestSuite and add the test case to it. Then instantiate and
    run the TestSuite.



"""

import os
from datetime import datetime

from pycopia import logging
from pycopia import reports

from . import core
from . import config
from . import environment
from .exceptions import TestRunnerError, ReportFindError
from .signals import (run_start, run_end, report_url,
                      run_comment, run_arguments, dut_version)
from .constants import TestResult

ModuleType = type(os)

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
            logging.loglevel_warning()

    def run(self, objects):
        """Main entry to run a list of runnable objects."""
        self.initialize()
        rv = self.run_objects(objects)
        self.finalize()
        return rv

    def run_object(self, obj):
        """Run a test object (object with run() function or method).

        Arguments:
            obj:
                A Python test object. This object must have a `run()` function
                or method that takes a configuration object and environment as
                its parameters.

        """

    def run_objects(self, objects):
        """Invoke the `run` method on a list of mixed runnable objects.

        Arguments:
            objects:
                A list of runnable objects. A runnable object is basically
                something that has a callable named "run" that takes a
                configuration object as a parameter.

        May raise TestRunnerError if an object is not runnable by this test
        runner.
        """
        rv = TestResult.INCOMPLETE
        testcases = []
        for obj in objects:
            objecttype = type(obj)
            if objecttype is type and issubclass(obj, core.TestCase):
                testcases.append(obj)
            elif isinstance(obj, core.TestSuite):
                obj.run()
                rv = obj.result
            elif issubclass(obj, core.UseCase):
                rv = obj.run(self.config, self.environment)
            elif objecttype is type and hasattr(obj, "run"):
                inst = obj(self.config, self.environment)
                rv = inst.run()
            elif objecttype is ModuleType and hasattr(obj, "run"):
                tcinst = core.TestCase(self.config, self.environment)
                for name, value in vars(tcinst).items():
                    if name == "run":
                        continue
                    if callable(value):
                        setattr(obj, name, value)
                obj.config = self.config
                obj.environment = self.environment
                rv = obj.run(self.config, self.environment)
                del obj.config
                del obj.environment
                for name, value in vars(tcinst).items():
                    if callable(value):
                        delattr(obj, name)
            else:
                logging.warn("{!r} is not a runnable object.".format(obj))
        if testcases:
            if len(testcases) > 1:
                rv = self.run_tests(testcases)
            else:
                rv = self.run_test(testcases[0])
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

        suite = core.TestSuite(self.config, self.environment,
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

        suite = core.TestSuite(self.config, self.environment, 
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
        # used as the timestamp for output location.
        runnertimestamp = datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
        # set resultsdir to full path where test run artifacts are placed.
        cf.resultsdir = os.path.join(
            os.path.expandvars(cf.get("resultsdirbase", "/var/tmp")),
            "{}-{}".format(runnertimestamp, cf.username))
        try:
            rpt = reports.get_report(cf)
        except ReportFindError as err:
            cf.UI.error(str(err))
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
        del self.environment
        del cf["report"]
        # remove log/results directory if it's empty.
        st = os.stat(cf.resultsdir)
        if st.st_nlink == 2:
            os.rmdir(cf.resultsdir)

    def report_global(self):
        """Report common, or global, information.
        Send some information to the user interface about the available
        parameters that a user may provide to run a test.
        """
        from pycopia.QA.db import models
        cf = self.config
        ui = cf.UI
        ui.printf("%YAvailable environment names for the "
                  "'%G--environmentname=%N' %Yoption%N:")
        ui.print_list(
            sorted([env.name for env in models.Environment.select()]))


def get_module_version(mod):
    """Get a version if present, else "unknown"."""
    try:
        return mod.__version__[1:-1].split(":")[-1].strip()
    except (AttributeError, IndexError):
        return "unknown"
