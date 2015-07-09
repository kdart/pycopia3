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
All exceptions for QA testing framwork.

"""

__all__ = ['TestFailError', 'TestIncompleteError', 'TestSuiteAbort', 'TestRunnerError',
        'ConfigError', 'ModelError', 'ModelAttributeError',
        'NoImplementationError', 'InvalidObjectError', 'InvalidTestError',
        'TestImplementationError',
        'ReportFindError',
        ]

class TestError(AssertionError):
    """TestError() Base class of testing errors.

    This is based on AssertionError so the same assertion catcher can be
    used to indicate test failure.
    """

# test core errors
class TestFailError(TestError):
    """Test case failed to meet the pass criteria."""

class TestIncompleteError(Exception):
    """Test case disposition could not be determined."""

class TestSuiteAbort(Exception):
    """Entire test suite must be aborted."""

class TestRunnerError(Exception):
    """Raised for a runtime error of the test runner."""

class TestImplementationError(Exception):
    """Raised if there is something wrong with the test implementation."""

# configuration errors
class ConfigError(Exception):
    """Raised when a configuration error is detected."""

# database errors
class ModelError(Exception):
    """Raised when something doesn't make sense for this model"""

class ModelAttributeError(ModelError):
    """Raised for errors related to models with attributes."""

class ModelValidationError(ModelError):
    """Raised when altering the database with invalid values."""

# loader errors
class LoaderError(Exception):
    """Base class for test loader errors."""

class NoImplementationError(LoaderError):
    """Raised when a test object has no automated implementation defined."""


class InvalidObjectError(LoaderError):
    """Raised when an attempt is made to instantiate a test object from the
    database, but the object in the database is marked invalid.
    """

class InvalidTestError(LoaderError):
    """Raised when a test is requested that cannot be run for some
    reason.
    """

# controller errors
class ControllerError(Exception):
    """Base class for controller related errors."""


# report errors
class ReportError(Exception):
    pass

class ReportFindError(ReportError):
    """Can't find requested report."""

