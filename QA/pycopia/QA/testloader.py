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

"""Load Python objects from database records.
"""


from pycopia import logging
from pycopia import module
from pycopia.textutils import identifier
from pycopia.QA import core
from pycopia.QA.exceptions import InvalidObjectError, InvalidTestError



def get_test_class(dbcase):
    """Return the implementation class of a TestCase, or None if not found.
    """
    if dbcase.automated and dbcase.valid:
        impl = dbcase.testimplementation
        if impl:
            obj = module.get_object(impl)
            if type(obj) is type and issubclass(obj, core.TestCase):
                return obj
            else:
                raise InvalidTestError("%r is not a Test class object." % (obj,))
        else:
            return None
    else:
        return None


def get_suite(dbsuite, config):
    """Get a Suite object.

    Return the implementation class of a TestSuite, or a generic Suite
    instance if not defined.
    """
    name = dbsuite.name
    if " " in name:
        name = identifier(name)
    impl = dbsuite.suiteimplementation
    if impl:
        try:
            obj = module.get_object(impl)
        except module.ObjectImportError:
            logging.warning("Did not find suite implementation {!r}.".format(impl))
        else:
            if type(obj) is type and issubclass(obj, core.TestSuite):
                return obj(config, name=name)
            else:
                raise InvalidObjectError("{!r} is not a TestSuite class object.".format(obj))
    return core.TestSuite(config, name=name)


