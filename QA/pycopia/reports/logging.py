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


