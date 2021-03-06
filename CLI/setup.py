#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab


from glob import glob
from setuptools import setup

NAME = "pycopia3-CLI"
VERSION = "1.0"

setup (name=NAME, version=VERSION,
    namespace_packages = ["pycopia"],
    packages = ["pycopia"],
#    install_requires = ['pycopia-core==dev'],
    dependency_links = [
            "http://www.pycopia.net/download/"
                ],
    scripts =glob("bin/*"),
    test_suite = "test.CLITests",

    description = "Pycopia framework for constructing POSIX/Cisco style command line interface tools.",
    long_description = """Pycopia framework for constructing POSIX/Cisco style command line
    interface tools.  Supports context commands, argument parsing,
    debugging aids.  Modular design allows you to wrap any object with a
    CLI tool.
    """,
    license = "LGPL",
    author = "Keith Dart",
    author_email = "keith@dartworks.biz",
    keywords = "pycopia CLI framework",
    url = "http://www.pycopia.net/",
    classifiers = ["Operating System :: POSIX",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Topic :: System :: Networking :: Monitoring",
                   "Intended Audience :: Developers"],
)


