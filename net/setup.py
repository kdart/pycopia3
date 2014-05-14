#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab


from glob import glob
from setuptools import setup, find_packages

NAME = "pycopia3-net"
VERSION = "1.0"

import platform

if platform.system() == "Linux":
    DATAFILES = [
        ('/etc/pycopia/ssl', glob("etc/ssl/*")),
    ]
    SCRIPTS = glob("bin/*")
else:
    DATAFILES = []
    SCRIPTS = []


setup (name=NAME, version=VERSION,
    namespace_packages = ["pycopia"],
    packages = find_packages(),
#    install_requires = ['pycopia-process>=1.0.dev-r138,==dev',
#                        'pycopia-CLI>=1.0.dev-r138,==dev',
#                        'pyopenssl>=0.13',
#                        'iso8601>=0.1.4',
#                        ],
    dependency_links = [
            "http://www.pycopia.net/download/"
                ],
    data_files = DATAFILES,
    scripts = SCRIPTS,
    test_suite = "test.NetTests",

    description = "General purpose network related modules.",
    long_description = """General purpose network related modules.
    Modules for updating DNS, modeling metworks, measuring networks, and a
    framework for the creation of arbitrary chat-style protocols.
    """,
    license = "LGPL",
    author = "Keith Dart",
    author_email = "keith@dartworks.biz",
    keywords = "pycopia networks",
    url = "http://www.pycopia.net/",
    #download_url = "ftp://ftp.pycopia.net/pub/python/%s.%s.tar.gz" % (NAME, VERSION),
    classifiers = ["Operating System :: POSIX",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Topic :: System :: Networking",
                   "Intended Audience :: Developers"],
)


