#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import sys
import os

import platform

from glob import glob
from setuptools import setup, find_packages

NAME = "pycopia3-QA"
VERSION = "1.0"


CACHEDIR="/var/cache/pycopia"

ISLINUX = platform.system() == "Linux"
if ISLINUX:
    DISTNAME, _version, _distid = platform.linux_distribution()
else:
    DISTNAME = ""


# Some services, such as the Pyro nameserver, are set up to run as the
# "tester" psuedo-user.  This also creates the "testers" group that testing
# personnel should also be a member of.
def system_setup():
    if ISLINUX:
        import os, pwd, grp
        if os.getuid() == 0:
            if DISTNAME.startswith("Gentoo"):
                try:
                    pwent = pwd.getpwnam("tester")
                except KeyError:
                    os.system("groupadd testers")
                    os.system("useradd -c Tester -g testers "
                    "-G users.uucp,audio,cdrom,dialout,video,games,usb,crontab,messagebus,plugdev "
                    "-m tester")
                    print ("Remember to change password for new user tester.")
                    #os.system("passwd tester")
                    pwent = pwd.getpwnam("tester")
                if not os.path.isdir(CACHEDIR):
                    tgrp = grp.getgrnam("testers")
                    os.mkdir(CACHEDIR)
                    os.chown(CACHEDIR, pwent.pw_uid, tgrp.gr_gid)
                    os.chmod(CACHEDIR, 0o770)


if ISLINUX:
    DATA_FILES = [
            ('/etc/pycopia', glob("etc/*.dist")),
    ]
    if DISTNAME.startswith("Gentoo"):
        DATA_FILES.append(('/etc/init.d', glob("etc/init.d/gentoo/*")))
    elif DISTNAME.startswith("Red") or DISTNAME.startswith("Cent"):
        DATA_FILES.append(('/etc/init.d', glob("etc/init.d/redhat/*")))

    if os.path.isdir("/etc/systemd/system"):
        DATA_FILES.append(('/etc/systemd/system', glob("etc/systemd/system/*")))
    SCRIPTS = glob("bin/*")

    WEBSITE = os.environ.get("WEBSITE", "localhost")
    DATA_FILES.extend([
        #(os.path.join("/var", "www", WEBSITE, 'htdocs'), glob("doc/html/*.html")),
        #(os.path.join("/var", "www", WEBSITE, 'cgi-bin'), glob("doc/html/cgi-bin/*.py")),
        (os.path.join("/var", "www", WEBSITE, 'media', 'js'), glob("media/js/*.js")),
        (os.path.join("/var", "www", WEBSITE, 'media', 'css'), glob("media/css/*.css")),
        #(os.path.join("/var", "www", WEBSITE, 'media', 'images'), glob("media/images/*.png")),
    ])

else:
    DATA_FILES = []
    SCRIPTS = []


setup (name=NAME, version=VERSION,
    namespace_packages = ["pycopia"],
    packages = find_packages(),
#    install_requires = [
#        'pycopia3-CLI',
#        'chardet>=2.2',
#        ],
    dependency_links = [
            "http://www.pycopia.net/download/"
                ],
    scripts = SCRIPTS,
    data_files = DATA_FILES,
    package_data = {"": ['*.glade']},
    test_suite = "test.QATests",

    description = "Pycopia packages to support professional QA roles.",
    long_description = """Pycopia packages to support professional QA roles.
    A basic QA automation framework. Provides base classes for test cases,
    test suites, test runners, reporting, lab models, terminal emulators,
    remote control, and other miscellaneous functions.
    """,
    license = "LGPL",
    author = "Keith Dart",
    author_email = "keith@dartworks.biz",
    keywords = "pycopia QA framework",
    url = "http://www.pycopia.net/",
    #download_url = "ftp://ftp.pycopia.net/pub/python/%s.%s.tar.gz" % (NAME, VERSION),
    classifiers = ["Operating System :: POSIX",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Topic :: Software Development :: Quality Assurance",
                   "Intended Audience :: Developers"],
)


if "install" in sys.argv:
    system_setup()

