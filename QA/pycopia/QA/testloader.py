#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
                raise InvalidTestError(
                    "{!r} is not a Test class object.".format(obj))
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
            logging.warning(
                "Did not find suite implementation {!r}.".format(impl))
        else:
            if type(obj) is type and issubclass(obj, core.TestSuite):
                return obj(config, name=name)
            else:
                raise InvalidObjectError(
                    "{!r} is not a TestSuite class object.".format(obj))
    return core.TestSuite(config, name=name)
