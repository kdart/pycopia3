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
The command-line interface to a test runner or reporter.  Adapts options given
on a command line to paramters to test cases and operates the test runner.
"""

import os

from pycopia import logging
from pycopia import getopt
from pycopia import module
from pycopia import UI
from pycopia.QA import testrunner


# Not in a docstring since docstrings don't exist in optimize mode.
TestRunnerInterfaceDoc = r"""
Invoke a test or test suite from a shell.

Usage:

    {name} [-h?dDvI] [-c|-f <configfile>] [-m <message>] [-e <environment>]
        [-r <reportname>] testargs...

    Where the arguments are test suite or test case module path names. If none
    are supplied a menu is presented.

    Options:

        -h -- Print help text and return.
        -d -- Turn on automatic debugging for test cases.
        -D -- Turn on automatic debugging for framework itself.
        -v -- Increase verbosity (This currently doesn't do anything).
        -I -- Set flag to skip interactive tests.
        -m <message> -- Add a comment to the test report.
        -c or -f <file> -- Merge in extra configuration file.
        -e <environmentname>  -- Name of Environment to use for this run.
        -r <reportname>  -- Name of report to use for this run.

    Long options (those with '--' prefix) must have values and are added to the
    configuration object that test cases receive.
"""


class TestRunnerInterface:
    """A Basic CLI interface to a TestRunner object.

    Instantiate with an instance of a TestRunner.

    Call the instance of this with an argv list to instantiate and run the
    given tests.
    """
    def __init__(self, testrunner):
        self.runner = testrunner

    def run(self, argv):
        """Run the test runner.

        Invoke the test runner by calling it.
        """
        cf = self.runner.config
        cf.flags.INTERACTIVE = True
        cf.flags.DEBUG = 0
        cf.flags.VERBOSE = 0
        optlist, longopts, args = getopt.getopt(argv[1:], "h?dDvIc:f:m:e:r:")
        for opt, optarg in optlist:
            if opt in ("-h", "-?"):
                print(TestRunnerInterfaceDoc.format(
                    name=os.path.basename(argv[0])))
                return
            elif opt == "-d":
                cf.flags.DEBUG += 1
            elif opt == "-D":
                from pycopia import autodebug  # noqa
            elif opt == "-v":
                cf.flags.VERBOSE += 1
            elif opt == "-I":
                cf.flags.INTERACTIVE = False
            elif opt == "-c" or opt == "-f":
                cf.mergefile(optarg)
            elif opt == "-m":
                cf.comment = optarg
            elif opt == "-r":
                cf.reportname = optarg
            elif opt == "-e":
                cf.environmentname = optarg

        cf.evalupdate(longopts)
        # original command line arguments saved for the report
        cf.arguments = [os.path.basename(argv[0])] + argv[1:]

        ui = UI.get_userinterface(themename="ANSITheme")
        if not args:
            from . import simplechooser
            args = simplechooser.choose_tests(ui)
        if not args:
            return 10
        objects, errors = module.get_objects(args)
        if errors:
            logging.warn("Errors found while loading test object:")
            for error in errors:
                logging.warn(error)
        if objects:
            cf.argv = args
            rv = self.runner.run(objects, ui)
            if rv is None:
                return 11
            else:
                try:
                    return int(rv)
                except TypeError:
                    return 12
        else:
            return len(errors) + 20


def runtest(argv):
    """Main function for CLI test runner."""
    tr = testrunner.TestRunner()
    tri = TestRunnerInterface(tr)
    return tri.run(argv)
