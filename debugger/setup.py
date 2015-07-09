

from setuptools import setup
from glob import glob

NAME = "pycopia3-debugger"
VERSION = "1.0"


setup (name=NAME, version=VERSION,
    namespace_packages = ["pycopia"],
    packages = ["pycopia"],
#    install_requires = [
#            'pycopia-aid>=1.0.dev-r138,==dev',
#            'pycopia-CLI>=1.0.dev-r138,==dev'],
    dependency_links = [
            "http://www.pycopia.net/download/"
                ],
    package_data = {
        'pycopia': ['*.doc'],
    },
    scripts =glob("bin/*"),
    test_suite = "test.DebuggerTests",

    description = "Enhanced Python debugger.",
    long_description = """Enhanced Python debugger.
    Like pdb, but has more inspection commands, colorized output, command
    history.
    """,
    license = "LGPL",
    author = "Keith Dart",
    author_email = "keith@kdart.com",
    keywords = "pycopia framework",
    url = "http://www.pycopia.net/",
    #download_url = "ftp://ftp.pycopia.net/pub/python/%s.%s.tar.gz" % (NAME, VERSION),
    classifiers = ["Operating System :: POSIX",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Topic :: System :: Networking :: Monitoring",
                   "Intended Audience :: Developers"],
)


