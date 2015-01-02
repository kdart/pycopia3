#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab


import sys
import os
import platform
from glob import glob
from setuptools import setup, find_packages

NAME = "pycopia3-WWW"
VERSION = "1.0"


if platform.system() == "Linux":

    WEBSITE = os.environ.get("WEBSITE", "localhost")

    DATAFILES = [
        ('/etc/pycopia', glob("etc/*.example") + glob("etc/*.dist")),
        ('/etc/pycopia/ssl', glob("etc/ssl/*")),
        ('/etc/pycopia/lighttpd', glob("etc/lighttpd/*")),
        (os.path.join(sys.prefix, 'libexec', 'pycopia'), glob("libexec/*")),
    ]
    distname, version, vid = platform.linux_distribution()
    if distname.startswith("Gentoo"):
        DATAFILES.append(('/etc/init.d', glob("etc/init.d/gentoo/*")))
    elif distname.startswith("Red"):
        DATAFILES.append(('/etc/init.d', glob("etc/init.d/redhat/*")))

    DATAFILES.extend([
        (os.path.join("/var", "www", WEBSITE, 'media', 'js'),
            glob("media/js/*.js")),
        (os.path.join("/var", "www", WEBSITE, 'media', 'css'),
            glob("media/css/*.css")),
        (os.path.join("/var", "www", WEBSITE, 'media', 'images'),
            glob("media/images/*.png")),
    ])
    SCRIPTS = glob("bin/*")
else:
    DATAFILES = []
    SCRIPTS = []


setup(name=NAME, version=VERSION,
      namespace_packages=["pycopia"],
      packages=find_packages(),
#      dependency_links=[
#          "http://www.pycopia.net/download/"
#      ],
      data_files=DATAFILES,
      scripts=SCRIPTS,
      test_suite="test.WWWTests",
      description="Pycopia WWW tools and web application framework.",
      long_description=open("README.md").read(),
      license="LGPL",
      author="Keith Dart",
      author_email="keith@dartworks.biz",
      keywords="pycopia WWW framework XHTML FCGI WSGI",
      url="http://www.pycopia.net/",
      classifiers=["Operating System :: POSIX",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries",  # noqa
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "Topic :: Software Development :: Quality Assurance",
          "Intended Audience :: Developers"],
)
