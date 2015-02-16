"""Collection of runtime reports.

"""

import locale

from pycopia import module
from pycopia.QA.signals import *
from pycopia.QA.exceptions import ReportFindError


class BaseReport:

    def initialize(self, title):
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

    def on_test_start(self, testcase, name=None, time=None):
        pass

    def on_test_end(self, testcase, time=None):
        pass

    def on_test_passed(self, testcase, message=None):
        pass

    def on_test_incomplete(self, testcase, message=None):
        pass

    def on_test_failure(self, testcase, message=None):
        pass

    def on_test_expected_failure(self, testcase, message=None):
        pass

    def on_test_abort(self, testcase, message=None):
        pass

    def on_test_info(self, testcase, message=None):
        pass

    def on_test_diagnostic(self, testcase, message=None):
        pass

    def on_test_arguments(self, testcase, arguments=None):
        pass

    def on_suite_start(self, testsuite, time=None):
        pass

    def on_suite_end(self, testsuite, time=None):
        pass

    def on_suite_info(self, testsuite, message=None):
        pass

    def on_run_start(self, runner, timestamp=None):
        pass

    def on_run_end(self, runner):
        pass

    def on_run_arguments(self, runner, message=None):
        pass

    def on_dut_version(self, testcase, version=None):
        pass

    def on_run_comment(self, runner, message=None):
        pass

    def on_report_url(self, runner, message=None, url=None):
        pass



def get_report(config):
    from . import default
    rname = config.get("reportname", "default")
    if rname.startswith("default"):
        if locale.getpreferredencoding() == 'UTF-8':
            return default.DefaultReportUnicode()
        else:
            return default.DefaultReport()
    elif "." in rname:
        robj = module.get_object(rname)
        return robj()
    else:
        raise ReportFindError("No report {} defined.".format(rname))

