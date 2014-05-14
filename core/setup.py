#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import sys

from setuptools import setup
from glob import glob

NAME = "pycopia3-core"
VERSION = "1.0"


if sys.platform.startswith("linux"):
    DATA_FILES = [('/etc/pycopia', glob("etc/*"))]
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
#    install_requires = ['pycopia-utils>=1.0.dev-r138,==dev'],
    package_data = {
        '': ['*.txt', '*.doc'],
    },
    test_suite = "test.CoreTests",
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
