Pycopia3 Overview
=================

The Pycopia package is a collection of Python (and some C) modules for use in
Python  applications. There is support for network management, "Web" frontends,
XML processing, process control, and more.

This version, pycopia3, is a redesign of
[Pycopia](https://code.google.com/p/pycopia/) using Python 3.4.  That framework
was developed for Python 2.7, and contains a lot of functionality that was
later added to standard Python over time (but implemented differently). So this
port also adopts some of the newer functionality found in Python3.4 and later.

Some noteworthy sub-packages and modules:

core, util    -- Some general purpose modules, such as OS device interfaces,
                 protocol modules, and more.

CLI           -- Toolkit for making interactive command tools fast and easy.

debugger      -- Enhanced Python debugger, using the CLI framework.

net           -- Modules for working with networks and servers, such as HTTP client.

QA            -- Complete systems framework (QA framework). Enables writing
                 simple, abstract test cases. A persistent storage model is
                 included that allows you to also manage test cases, report
                 results, and manage lab equipment as well.

Most of this library is mostly governed by the Lesser GNU Public License
(LGPL). Some modules are under the Apache 2.0 license.


INSTALL
-------

See the INSTALL file.

NOTE: The install operation requires that the sudo command be configured for you.

You should already have the following installed for a complete installation.

### Non-Python packages (with dev packages)

- postgres server
- libsmi (sometimes names libsmi2)
- openssl

### Python packages

- pytz
- cython
- pyopenssl

### Optional Python packages (future use)

- iso8601
- chardet
- pyro4
- pycrypto
- urwid
- sqlalchemy
- psycopg
- sphinx


Install script
--------------

The top-level setup script helps with dealing with all sub-packages at
once. It also provides an installer for a developer mode.

Invoke it like a standard setup.py script. However, Any names after the
operation name are taken as sub-package names that are operated on. If no
names are given then all packages are operated on.

Commands:

<pre>
 list             -- List available subpackages. These are the names you may optionally supply.
 publish          -- Put source distribution on pypi.
 build            -- Run setuptools build phase on named sub-packages (or all of them).
 install          -- Run setuptools install phase.
 install_scripts  -- Install all toplevel scripts.
 eggs             -- Build distributable egg package.
 rpms             -- Build RPMs on platforms that support building RPMs.
 msis             -- Build Microsoft .msi on Windows.
 wininst          -- Build .exe installer on Windows.
 develop          -- Developer mode, as defined by setuptools. Set per user. Allows
                     running from workspace.
 clean            -- Run setuptools clean phase.
 squash           -- Squash (flatten) all named sub-packages into single tree
                     in $PYCOPIA_SQUASH, or user site-directory if no $PYCOPIA_SQUASH defined.
                     This also removes the setuptools runtime dependency.
</pre>
Most regular setuptools commands also work. They are passed through by
default.


