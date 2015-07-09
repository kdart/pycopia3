#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

"""
Blinker signals used by the QA testing framework.
"""

__all__ = ["test_start", "test_end", "test_passed", "test_incomplete", "test_failure",
        "test_expected_failure", "test_abort", "test_info", "test_diagnostic",
        "test_arguments", "suite_start", "suite_end", "suite_info", "run_start",
        "run_end", "dut_version", "report_url", "run_comment", "run_arguments",
        ]

from blinker import Namespace

# Blinker signals that are emitted at various times during a test run.
_signals = Namespace()

# test case events
test_start = _signals.signal('test-start')
test_end = _signals.signal('test-end')
test_passed = _signals.signal('test-passed')
test_incomplete = _signals.signal('test-incomplete')
test_failure = _signals.signal('test-failure')
test_expected_failure = _signals.signal('test-expected-failure')
test_abort = _signals.signal('test-abort')
test_info = _signals.signal('test-info')
test_diagnostic = _signals.signal('test-diagnostic')
test_arguments = _signals.signal('test-arguments')

# suite events
suite_start = _signals.signal('suite-start')
suite_end = _signals.signal('suite-end')
suite_info = _signals.signal('suite-info')

# runner events
run_start = _signals.signal('run-start')
run_end = _signals.signal('run-end')
run_arguments = _signals.signal('run-arguments')
run_comment = _signals.signal('report-comment')

# extra informational
dut_version = _signals.signal('dut-version')
report_url = _signals.signal('report-url')

