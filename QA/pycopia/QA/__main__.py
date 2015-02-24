#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.

"""
QA module runs unit tests when run as module.
"""

import sys
import pkgutil

from pycopia import module
from pycopia import UI
from pycopia.aid import NULL
from pycopia.QA import testrunner
from pycopia.QA import simplechooser
from pycopia.QA import core
from pycopia.QA.db import config
from pycopia.QA.db import models


def _init_db():
    """Initialize a mock database with minimal entries."""
    models.connect("sqlite://:memory:")
    models.database.create_tables(
        [getattr(models, name) for name in models.TABLES + models._ASSOC_TABLES],
        safe=True)
    with models.database.atomic():
        models.Environments.create(name="default")
        rn = models.Config.create(name="root", user=None, parent=None,
                value=NULL)
        flags = models.Config.create(name="flags", user=None, parent=rn,
                value=NULL)
        root = config.Container(rn)
        flags = config.Container(flags)
        flags.DEBUG = 1
        flags.VERBOSE = 0
        root["logbasename"] = "unittest.log"
        root["logfiledir"] = "/var/tmp"
        root["resultsdirbase"] = '/var/www/localhost/htdocs/testresults'
        root["documentroot"] = "/var/www/localhost"
        root["baseurl"] = "http://localhost"


def all_tests(ui):
    try:
        from testcases import unittests
    except ImportError:
        logging.warn("Cannot find 'testcases.unittests' base package.")
        return []

    modnames = []
    runnables = []
    for finder, name, ispkg in pkgutil.walk_packages(
            unittests.__path__, unittests.__name__ + '.'):
        if ispkg:
            continue
        if "._" not in name:
            modnames.append(name)

    for modname in modnames:
        try:
            mod = module.get_module(modname)
        except module.ModuleImportError:
            ui.warning("  Warning: could not import '{}'".format(modname))
            continue
        except:
            ex, val, tb = sys.exc_info()
            ui.warning("  Warning: could not import '{}'".format(modname))
            ui.error("      {}: {}".format(ex, val))
            continue
        for attrname in dir(mod):
            obj = getattr(mod, attrname)
            if type(obj) is type:
                if issubclass(obj, core.UseCase):
                    runnables.append("{}.{}".format(modname, obj.__name__))
    return runnables


def unittest(argv):
    args = argv[1:]
    _init_db()
    tr = testrunner.TestRunner("sqlite://:memory:")
    ui = UI.get_userinterface(themename="ANSITheme")
    if not args:
        args = all_tests(ui)
    if not args:
        return
    objects, errors = module.get_objects(args)
    if errors:
        print("Errors found while loading test object:")
        for error in errors:
            print(error)
    if objects:
        tr.run(objects, ui)


unittest(sys.argv)
