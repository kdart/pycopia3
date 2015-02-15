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

"""
Report that writes to syslog via logging module.

"""

from pycopia import logging
from pycopia.reports import BaseReport
from pycopia.QA.signals import *


class LoggingReport(BaseReport):

    def initialize(self, title):
        super().initialize(title)
        self._logger = logging.Logger(title, usestderr=False)

    def finalize(self):
        super().finalize()
        self._logger.close()
        self._logger = None

    def on_test_start(self, testcase, name=None, time=None):
        self._logger.notice("TEST START: {!s}".format(name))

    def on_test_end(self, testcase, time=None):
        self._logger.notice("TEST END: {!s}".format(testcase.test_name))

    def on_test_passed(self, testcase, message=None):
        self._logger.notice("{}: PASSED {}".format(testcase.test_name, message))

    def on_test_incomplete(self, testcase, message=None):
        self._logger.notice("{}: INCOMPLETE {}".format(testcase.test_name, message))

    def on_test_failure(self, testcase, message=None):
        self._logger.notice("{}: FAILED {}".format(testcase.test_name, message))

    def on_test_expected_failure(self, testcase, message=None):
        self._logger.notice("{}: EXPECTED FAILED {}".format(testcase.test_name, message))

    def on_test_abort(self, testcase, message=None):
        self._logger.error("{}: ABORTED {}".format(testcase.test_name, message))

    def on_test_info(self, testcase, message=None):
        self._logger.info("{}: INFO {}".format(testcase.test_name, message))

    def on_test_diagnostic(self, testcase, message=None):
        self._logger.info("{}: DIAGNOSTIC {}".format(testcase.test_name, message))

    def on_test_arguments(self, testcase, arguments=None):
        if arguments:
            self._logger.info("{}: arguments: {}".format(testcase.test_name, arguments))

    def on_suite_start(self, testsuite, time=None):
        self._logger.info("SUITE START: {!s}".format(testsuite.test_name))

    def on_suite_end(self, testsuite, time=None):
        self._logger.info("SUITE END: {!s}".format(testsuite.test_name))

    def on_suite_info(self, testsuite, message=None):
        self._logger.info("{}: SUITE INFO: {!s}".format(testsuite.test_name, message))

    def on_run_start(self, runner, timestamp=None):
        self._logger.info("RUN START: {!s}".format(timestamp))

    def on_run_end(self, runner):
        self._logger.info("RUN END")

    def on_run_arguments(self, runner, message=None):
        self._logger.info("runner: arguments: {!s}".format(message))

    def on_dut_version(self, testcase, version=None):
        self._logger.info("{}: DUT: {}".format(testcase.test_name, version))

    def on_run_comment(self, runner, message=None):
        self._logger.info("runner: comment: {}".format(message))


