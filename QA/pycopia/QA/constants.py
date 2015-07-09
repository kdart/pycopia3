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

"""QA Universal constants and enumerations.

Possible test outcomes:

- TestResult.PASSED: execute() test passed (criteria was met), and the suite
  may continue.

- TestResult.FAILED: execute() failed (criteria was not met), but the suite can
  continue. You may also raise a TestFailError exception.

- TestResult.INCOMPLETE: execute() could not complete, and the pass/fail
  criteria could not be determined. but the suite may continue. You may also
  raise a TestIncompleteError exception.

- TestResult.ABORTED: execute() could not complete, and the suite cannot
  continue.

- TestResult.NA: A result that is not applicable (e.g. it is a holder of
  tests).

- TestResult.EXPECTED_FAIL: Means the test is failing due to a bug, and is
  already known to fail.

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
    """Types of objects that have test result records."""
    UseCase = 0
    TestSuite = 1
    Test = 2
    TestRunner = 3
    unknown = 4


class ValueType(enum.IntEnum):
    """Basic types that model.AttributeType may have."""
    Object = 0
    String = 1
    Integer = 2
    Float = 3
    Boolean = 4


class TestCaseType(enum.IntEnum):
    """Type of test case, where it fits in the development cycle."""
    Unknown = 0
    Unit = 1
    System = 2
    Integration = 3
    Regression = 4
    Performance = 5


class Status(enum.IntEnum):
    """Status of something, like a test case."""
    Unknown = 0
    New = 1
    Reviewed = 2
    Preproduction = 3
    Production = 4
    Deprecated = 5
    Obsolete = 6


class Priority(enum.IntEnum):
    """Priority of something, such as a test case."""
    Unknown = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4
    P5 = 5


class Likelihood(enum.IntEnum):
    """Approximate likelihood that an event may occur."""
    Unknown = 0
    VeryLikely = 1
    Likely = 2
    Possible = 3
    Unlikely = 4
    VeryUnlikely = 5


class Severity(enum.IntEnum):
    """Severity, or impact that an item may have on something if it did not
    exist.
    """
    Unknown = 0
    Trivial = 1
    Annoyance = 2
    CauseDifficulty = 3
    MinorLossHasReplacement = 4
    MinorLoss = 5
    MajorLoss = 6
