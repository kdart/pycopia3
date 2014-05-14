#!/usr/bin/python2.7
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab


import os
from setuptools import setup

NAME = "pycopia3-aid"

VERSION = "1.0"


setup (name=NAME, version=VERSION,
    namespace_packages = ["pycopia"],
    packages = ["pycopia",],
    test_suite = "test.AidTests",

    author = "Keith Dart",
    author_email = "keith@dartworks.biz",
    description = "General purpose modules that aid or extend standard modules.",
    long_description = """General purpose modules that aid or extend standard modules.
    Some new useful types, such as Enums acting as "named numbers", a NULL type, and others.""",
    license = "LGPL",
    keywords = "pycopia framework Python extensions",
    url = "http://www.pycopia.net/",
    classifiers = ["Programming Language :: Python",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Intended Audience :: Developers"],
)

