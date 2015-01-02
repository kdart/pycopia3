#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import sys

from glob import glob
from setuptools import setup

NAME = "pycopia3-process"
VERSION = "1.0"


if sys.platform not in ("win32", "cli"):
    DATA_FILES = [
        ('/etc/pycopia', glob("etc/*")),
    ]
else:
    DATA_FILES = []

setup(name=NAME, version=VERSION,
      namespace_packages=["pycopia"],
      packages=["pycopia"],
      test_suite="test.ProcessTests",
#    install_requires=['pycopia-core>=1.0.dev-r138,==dev'],
      data_files=DATA_FILES,
      description="Modules for running, interacting with, and managing processes.",  # noqa
      long_description=open("README.md").read(),
      license="LGPL",
      author="Keith Dart",
      keywords="pycopia framework",
      url="http://www.pycopia.net/",
      classifiers=["Operating System :: POSIX",
                   "Topic :: Software Development :: Libraries :: Python Modules",  # noqa
                   "Topic :: System :: Operating System",
                   "Intended Audience :: Developers"],
)
