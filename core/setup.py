#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import sys

from setuptools import setup
from distutils.extension import Extension
from glob import glob

NAME = "pycopia3-core"
VERSION = "1.0"

EXTENSIONS = []

if sys.platform.startswith("linux"):
    DATA_FILES = [('/etc/pycopia', glob("etc/*"))]
    EXTENSIONS.append(Extension('pycopia.netstring', ['netstring.c']))
else:
    DATA_FILES = []


setup (name=NAME, version=VERSION,
    namespace_packages = ["pycopia"],
    packages = ["pycopia",
    "pycopia.physics",
    "pycopia.ISO",
    "pycopia.inet",
    "pycopia.OS",
    "pycopia.OS.Win32",
    "pycopia.OS.Linux",
    "pycopia.OS.Linux.proc",
    "pycopia.OS.Linux.proc.net",
    ],
    ext_modules = EXTENSIONS,
#    install_requires = ['pycopia-utils>=1.0.dev-r138,==dev'],
    package_data = {
        '': ['*.txt', '*.doc'],
    },
    test_suite = "test",
    data_files = DATA_FILES,
    scripts = glob("bin/*"),
    zip_safe = False,

    description = "Core components of the Pycopia application framework.",
    long_description = """Core components of the Pycopia application framework.
    Modules used by other PYcopia packages, that you can also use in your
    applications.
    """,
    license = "LGPL",
    author = "Keith Dart",
    author_email = "keith@dartworks.biz",
    keywords = "pycopia framework core Linux",
    url = "http://www.pycopia.net/",
    classifiers = ["Operating System :: POSIX",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Intended Audience :: Developers"],
)
