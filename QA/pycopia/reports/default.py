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
Default report used when running tests.

Supports simple, colored reports for both unicode and non-unicode terminals.

Also servers as usage example of TestCase signals.

"""

import sys

from pycopia.QA.signals import *
from pycopia.QA.constants import TestResult


RESET = "\x1b[0m" # aka NORMAL

ITALIC_ON = "\x1b[3m"
ITALIC_OFF = "\x1b[23m"

UNDERLINE_ON = "\x1b[4m"
UNDERLINE_OFF = "\x1b[24m"

INVERSE_ON = "\x1b[7m"
INVERSE_OFF = "\x1b[27m"

RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
GREY = "\x1b[37m"

LT_RED = "\x1b[31:01m"
LT_GREEN = "\x1b[32:01m"
LT_YELLOW = "\x1b[33;01m"
LT_BLUE = "\x1b[34;01m"
LT_MAGENTA = "\x1b[35;01m"
LT_CYAN = "\x1b[36;01m"
WHITE = "\x1b[01m" # aka INTENSE or BRIGHT,

RED_BACK = "\x1b[41m"
GREEN_BACK = "\x1b[42m"
YELLOW_BACK = "\x1b[43m"
BLUE_BACK = "\x1b[44m"
MAGENTA_BACK = "\x1b[45m"
CYAN_BACK = "\x1b[46m"
WHITE_BACK = "\x1b[47m"

#                 UL  hor   vert  UR  LL   LR
_BOXCHARS = {1: ['┏', '━', '┃', '┓', '┗', '┛',],
             2: ['╔', '═', '║', '╗', '╚', '╝',],
             3: ['┌', '─', '│', '┐', '└', '┘',],
}


_BOXCHARS_A = {1: ['+', '=', '|', '+', '+', '+',],
               2: ['+', '-', '|', '+', '+', '+',],
               3: ['+', '+', '|', '+', '+', '+',],
}



def white(text):
    return WHITE + text + RESET

def inverse(text):
    return INVERSE_ON + text + INVERSE_OFF

def green(text):
    return GREEN+text+RESET

def red(text):
    return RED+text+RESET

def blue(text):
    return BLUE + text + RESET

def yellow(text):
    return YELLOW+text+RESET

def cyan(text):
    return CYAN+text+RESET

def lt_red(text):
    return LT_RED+text+RESET

def inverse_red(text):
    return INVERSE_ON+RED+text+RESET+INVERSE_OFF


class BaseReport:

    def initialize(self, title="Title", file=None):
        pass

    def finalize(self):
        pass


class DefaultReport(BaseReport):

    def initialize(self, title, file=None):
        if file is None:
            file = sys.stdout
        self._file = file
        test_start.connect(self.on_test_start)
        test_end.connect(self.on_test_end)
        test_passed.connect(self.on_test_passed)
        test_incomplete.connect(self.on_test_incomplete)
        test_failure.connect(self.on_test_failure)
        test_expected_failure.connect(self.on_test_expected_failure)
        test_abort.connect(self.on_test_abort)
        test_info.connect(self.on_test_info)
        test_diagnostic.connect(self.on_test_diagnostic)
        test_arguments.connect(self.on_test_arguments)
        suite_start.connect(self.on_suite_start)
        suite_end.connect(self.on_suite_end)
        suite_info.connect(self.on_suite_info)
        run_start.connect(self.on_run_start)
        run_end.connect(self.on_run_end)
        run_arguments.connect(self.on_run_arguments)
        dut_version.connect(self.on_dut_version)
        run_comment.connect(self.on_run_comment)
        report_url.connect(self.on_report_url)
        print("{0:^80.80s}".format(inverse(title)), file=file)

    def finalize(self):
        test_start.disconnect(self.on_test_start)
        test_end.disconnect(self.on_test_end)
        test_passed.disconnect(self.on_test_passed)
        test_incomplete.disconnect(self.on_test_incomplete)
        test_failure.disconnect(self.on_test_failure)
        test_expected_failure.disconnect(self.on_test_expected_failure)
        test_abort.disconnect(self.on_test_abort)
        test_info.disconnect(self.on_test_info)
        test_diagnostic.disconnect(self.on_test_diagnostic)
        test_arguments.disconnect(self.on_test_arguments)
        suite_start.disconnect(self.on_suite_start)
        suite_end.disconnect(self.on_suite_end)
        suite_info.disconnect(self.on_suite_info)
        run_start.disconnect(self.on_run_start)
        run_end.disconnect(self.on_run_end)
        run_arguments.disconnect(self.on_run_arguments)
        dut_version.disconnect(self.on_dut_version)
        run_comment.disconnect(self.on_run_comment)
        report_url.disconnect(self.on_report_url)
        print("{0}".format(inverse("Done.")), file=self._file)
        self._file = None

    def on_test_start(self, testcase, name=None, time=None):
        print("  {!s}: start {!s}".format(blue(str(time.time())), name), file=self._file)

    def on_test_end(self, testcase, time=None):
        print("    {!s}: test end.".format(blue(str(time.time()))), file=self._file)

    def on_test_passed(self, testcase, message=None):
        print("    {}: {!s}".format(green("PASSED"), message), file=self._file)

    def on_test_incomplete(self, testcase, message=None):
        print("    {}: {!s}".format(yellow("INCOMPLETE"), message), file=self._file)

    def on_test_failure(self, testcase, message=None):
        print("    {}: {!s}".format(red("FAILED"), message), file=self._file)

    def on_test_expected_failure(self, testcase, message=None):
        print("    {}: {!s}".format(lt_red("EXPECTED FAILED"), message), file=self._file)

    def on_test_abort(self, testcase, message=None):
        print("    {}: {!s}".format(inverse_red("ABORTED"), message), file=self._file)

    def on_test_info(self, testcase, message=None):
        print("    info: {!s}".format(message), file=self._file)

    def on_test_diagnostic(self, testcase, message=None):
        print((MAGENTA+"  diagnostic:"+RESET+" {!s}").format(message), file=self._file)

    def on_test_arguments(self, testcase, arguments=None):
        if arguments:
            print((CYAN+"    arguments:"+RESET+" {!s}").format(arguments), file=self._file)

    def on_suite_start(self, testsuite, time=None):
        print("{!s}: suite start {!s}".format(
                blue(str(time.time())), white(testsuite.test_name)), file=self._file)

    def on_suite_end(self, testsuite, time=None):
        print("  {!s}: suite end.".format(blue(str(time.time()))), file=self._file)

    def on_suite_info(self, testsuite, message=None):
        print("  info: {!s}".format(message), file=self._file)

    def on_run_start(self, runner, timestamp=None):
        print("{!s}: runner start.".format(blue(timestamp)), file=self._file)

    def on_run_end(self, runner):
        print("runner end.", file=self._file)

    def on_run_arguments(self, runner, message=None):
        print((CYAN+"runner arguments:"+RESET+" {!s}").format(message), file=self._file)

    def on_dut_version(self, testcase, version=None):
        print(("DUT version: {!s}").format(version), file=self._file)

    def on_run_comment(self, runner, message=None):
        print("comment: {!s}".format(message), file=self._file)

    def on_report_url(self, runner, message=None, url=None):
        print("URL: {!s}: {!s}".format(message, url), file=self._file)



class DefaultReportUnicode(DefaultReport):

    def on_test_passed(self, testcase, message=None):
        print("    {}: {!s}".format(green('✔'), message), file=self._file)

    def on_test_incomplete(self, testcase, message=None):
        print("    {}: {!s}".format(yellow('⁇'), message), file=self._file)

    def on_test_failure(self, testcase, message=None):
        print("    {}: {!s}".format(red('✘'), message), file=self._file)

    def on_test_expected_failure(self, testcase, message=None):
        print("    {}: {!s}".format(cyan('✘'), message), file=self._file)

    def on_test_abort(self, testcase, message=None):
        print("    {}: {!s}".format(inverse_red('‼'), message), file=self._file)

    def on_run_start(self, runner, timestamp=None):
        UL, hor, vert, UR, LL, LR = _BOXCHARS[1]
        text = "Start run at {}".format(timestamp)
        tt = "{}{}{}".format(UL, hor*(len(text)+2), UR)
        bt = "{}{}{}".format(LL, hor*(len(text)+2), LR)
        ml = "{} {} {}".format(vert, text, vert)
        print(tt, ml, bt, sep="\n", file=self._file)

    def on_suite_start(self, testsuite, time=None):
        UL, hor, vert, UR, LL, LR = _BOXCHARS[2]
        text = "Start {} at {}".format(testsuite.test_name, time.time())
        tt = "{}{}{}".format(UL, hor*(len(text)+2), UR)
        bt = "{}{}{}".format(LL, hor*(len(text)+2), LR)
        ml = "{} {} {}".format(vert, text, vert)
        print(tt, ml, bt, sep="\n", file=self._file)

