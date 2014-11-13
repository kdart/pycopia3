#!/usr/bin/python

"""QA Universal constants and enumerations.

Possible test outcomes:

- TestResult.PASSED: execute() test passed (criteria was met), and the suite may continue.

- TestResult.FAILED: execute() failed (criteria was not met), but the suite can
  continue. You may also raise a TestFailError exception.

- TestResult.INCOMPLETE: execute() could not complete, and the pass/fail criteria
  could not be determined. but the suite may continue. You may also raise
  a TestIncompleteError exception.

- TestResult.ABORTED: execute() could not complete, and the suite cannot continue.

- TestResult.NA: A result that is not applicable (e.g. it is a holder of tests).

- TestResult.EXPECTED_FAIL: Means the test is failing due to a bug, and is already
  known to fail.

"""

import enum

class TestResult(enum.IntEnum):
    PASSED = 0
    FAILED = 1
    INCOMPLETE = 3
    EXPECTED_FAIL = 4
    ABORTED = 5
    NA = 6

    def is_passed(self):
        return self.value == TestResult.PASSED

    def not_passed(self):
            return self.value in (TestResult.FAILED, TestResult.EXPECTED_FAIL,
                    TestResult.INCOMPLETE, TestResult.ABORT)

    def is_failed(self):
        return self.value == TestResult.FAILED

    def is_incomplete(self):
        return self.value == TestResult.INCOMPLETE


class ObjectTypes(enum.IntEnum):
    UseCase = 0
    TestSuite = 1
    Test = 2
    TestRunner = 3
    unknown = 4


