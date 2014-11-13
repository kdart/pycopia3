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

"""

import sys
import os
from errno import EEXIST
from datetime import datetime

from pycopia import debugger
from pycopia import logging
from pycopia.QA import core
from pycopia import reports

from pycopia.QA.signals import (run_start, run_end, report_url,
        run_comment, run_arguments, dut_version)
from pycopia.QA.constants import TestResult
from pycopia.QA.exceptions import TestRunnerError, ReportFindError


class TestRunner:
    """Runs test objects.

    Handled running objects, initializing reports,
    running tests and cleaning up afterwards.
    """
    def __init__(self, config):
        self.config = config
        self.config.options_override = {}
        self.config.arguments = []
        if config.flags.DEBUG:
            logging.loglevel_debug()
        else:
            logging.loglevel_warning()

    def set_options(self, opts):
        if isinstance(opts, dict):
            self.config.options_override = opts
        else:
            raise ValueError("Options must be dictionary type.")

    def run_object(self, obj):
        """Run a test object (object with run() function or method).

        Arguments:
            obj:
                A Python test object.    This object must have a `run()` function
                or method that takes a configuration object as it's single
                parameter. It should also have a `test_name` attribute.

        """
        cf = self.config
        basename = "_".join(obj.test_name.split("."))
        #cf.logbasename = basename + "-" + cf.runnertimestamp + ".log"
        # resultsdir is where you would place any resulting data files. This
        # is also where any report object or log files are placed.
        cf.resultsdir = os.path.join(
            os.path.expandvars(cf.get("resultsdirbase", "/var/tmp")),
            "%s-%s-%s" % (basename, cf.username, cf.runnertimestamp))
        cf.evalupdate(cf.options_override)
        self._create_results_dir()
        self._set_report_url()
        # run the test object!
        return obj.run(cf)

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
        rv = 0
        testcases = []
        for obj in objects:
            objecttype = type(obj)
            if objecttype is type and issubclass(obj, core.TestCase):
                testcases.append(obj)
            elif isinstance(obj, core.TestSuite):
                rv = self.run_object(obj)
            elif objecttype is type and hasattr(obj, "run"):
                # a bare class uses as a subcontainer of test or suite constructor.
                rv = self.run_class(obj)
            else:
                logging.warn("%r is not a runnable object." % (obj,))
        if testcases:
            if len(testcases) > 1:
                rv = self.run_tests(testcases)
            else:
                args = []
                kwargs = {}
                opts = self.config.options_override.copy()
                for name, value in list(opts.items()):
                    if name.startswith("arg"):
                        try:
                            index = int(name[3]) # use --arg1=XXX to place argument XXX
                        except (ValueError, IndexError):
                            logging.warn("{!r} not converted to argument.".format(name))
                        else:
                            try:
                                args[index] = value
                            except IndexError:
                                need = index - len(args)
                                while need:
                                    args.append(None)
                                    need -= 1
                                args.append(value)
                        del self.config.options_override[name]
                        del self.config[name]
                    elif name.startswith("kwarg_"): # use --kwarg_XXX to place keyword argument XXX
                        kwargs[name[6:]] = value
                        del self.config.options_override[name]
                        del self.config[name]
                rv = self.run_test(testcases[0], *args, **kwargs)
        return rv

    def run_class(self, cls):
        """Run a container class inside a module.

        Arguments:
            class with run method:
                A class object with a static run() method that takes a configuration
                object as it's single parameter.

        Returns:
            The return value of the class's run() method, or FAILED if the
            module raised an exception.
        """
        rpt = self.config.report
        cls.test_name = ".".join([cls.__module__, cls.__name__])
        ID = get_module_version(sys.modules[cls.__module__])
        try:
            rv = self.run_object(cls)
        except KeyboardInterrupt:
            raise
        except:
            ex, val, tb = sys.exc_info()
            if self.config.flags.DEBUG:
                debugger.post_mortem(tb, ex, val)
            return TestResult.INCOMPLETE
        return rv

    def run_suite(self, suite):
        """Run a TestSuite object.

        Given a pre-populated TestSuite object, run it after initializing
        configuration and report objects.

        Arguments:
            suite:
                An instance of a core.TestSuite class or subclass. This should
                already have Test objects added to it.

        Returns:
            The return value of the suite. Should be PASSED or FAILED.

        """
        if not isinstance(suite, core.TestSuite):
            raise TestRunnerError("Must supply TestSuite object.")
        return self.run_object(suite)

    def run_test(self, testclass, *args, **kwargs):
        """Run a test single test class with arguments.

        Runs a single test class with the provided arguments. Test class
        is placed in a temporary TestSuite.

        Arguments:
            testclass:
                A class that is a subclass of core.Test. Any extra arguments given
                are passed to the `execute()` method when it is invoked.

        Returns:
            The return value of the Test instance. Should be PASSED, FAILED,
            INCOMPLETE, or ABORT.
        """

        suite = core.TestSuite(self.config, name="%sSuite" % testclass.__name__)
        suite.add_test(testclass, *args, **kwargs)
        return self.run_object(suite)

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

        suite = core.TestSuite(self.config, name="RunTestsTempSuite")
        suite.add_tests(testclasses)
        return self.run_object(suite)

    def _create_results_dir(self):
        """Make results dir, don't worry if it already exists."""
        try:
            os.mkdir(self.config.resultsdir)
        except OSError as error:
            if error[0] == EEXIST:
                pass
            else:
                raise

    def _set_report_url(self):
        """Construct a URL for finding the report and test produced data.

        If the configuration has a `baseurl` and `documentroot` defined then
        the results location is available by web server and a URL is sent to
        the report. If not, the a ``file`` URL is sent to the report.
        """
        cf = self.config
        baseurl = cf.get("baseurl")
        documentroot = cf.get("documentroot")
        resultsdir = cf.resultsdir
        if baseurl and documentroot:
            report_url.send(self, message="results location",
                    url=baseurl+resultsdir[len(documentroot):])
        else:
            report_url.send(self, message="File location",
                    url="file://" + resultsdir)

    def initialize(self):
        """Perform any initialization needed by the test runner.

        Initializes report. Sends runner and header messages to the report.
        """
        cf = self.config
        cf.username = os.environ["USER"]
        # used as the timestamp for output location.
        cf.runnertimestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        try:
            rpt = reports.get_report(cf)
        except ReportFindError as err:
            cf.UI.error(str(err))
            raise TestRunnerError("Cannot continue without report.")
        rpt.initialize(title=" ".join(cf.get("argv", ["unknown"])))
        cf.report = rpt
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


    def finalize(self):
        """Perform any finalization needed by the test runner.
        Sends runner end messages to report. Finalizes report.
        """
        cf = self.config
        rpt = cf.report
        rpt.finalize()
        del cf["report"]

    def report_global(self):
        """Report common, or global, information.
        Send some information to the user interface about the available
        parameters that a user may provide to run a test.
        """
        from pycopia.QA.db import models
        cf = self.config
        ui = cf.UI
        ui.printf("%YAvailable environment names for the '%G--environmentname=%N' %Yoption%N:")
        ui.print_list(sorted([env.name for env in models.Environment.select()]))



def get_module_version(mod):
    try:
        return mod.__version__[1:-1].split(":")[-1].strip()
    except (AttributeError, IndexError): # Should be there, but don't worry if it's not.
        return "unknown"

