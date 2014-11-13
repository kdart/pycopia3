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

