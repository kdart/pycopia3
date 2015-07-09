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

"""
Runtime environment for test cases.

Holds special methods for getting information and controllers from environment
equipment.

The EnvironmentRuntime is the top-level entry point for accessing all
environmantal data, including the DUT.
"""

import sys
import gc

from pycopia import logging
from pycopia import scheduler

from pycopia.QA.exceptions import ConfigError
from pycopia.QA.db import models
from pycopia.QA import controller


class EnvironmentRuntime:
    def __init__(self, environmentrow):
        self._environment = environmentrow
        self._eqcache = {}
        d = {}
        for prop in environmentrow.attributes:
            d[prop.type.name] = prop.value
        self._attributes = d

    def __getitem__(self, name):
        return self._attributes[name]

    def get(self, name, default=None):
        return self._attributes.get(name, default)

    def __str__(self):
        s = []
        for teq in self._environment.testequipment:
            s.append(str(teq))
        return "%s:\n  %s" % (self._environment.name, "\n  ".join(s))

    def get_equipment(self, name, role="unspecified"):
        """Get any equipment runtime from the configuration by name."""
        try:
            eqrow = models.Equipment.select().where(
                models.Equipment.name.contains(name)).get()
        except models.DoesNotExist as err:
            raise ConfigError(
                "Bad equipment name {!r}: {!s}".format(name, err))
        return EquipmentRuntime(eqrow, role)

    @property
    def DUT(self):
        try:
            return self._eqcache["DUT"]
        except KeyError:
            pass
        eq = EquipmentRuntime(self._environment.get_DUT(), "DUT")
        self._eqcache["DUT"] = eq
        return eq

    @property
    def owner(self):
        return self._environment.owner

    @owner.setter
    def owner(self, name):
        user = models.User.get_by_username(name)
        self._environment.owner = user

    def get_role(self, rolename):
        try:
            return self._eqcache[rolename]
        except KeyError:
            pass
        eq = self._environment.get_equipment_with_role(rolename)
        eq = EquipmentRuntime(eq, rolename)
        self._eqcache[rolename] = eq
        return eq

    def get_all_with_role(self, rolename):
        eqlist = self._environment.get_all_equipment_with_role(rolename)
        first = self._eqcache.get(rolename)
        if first:
            rlist = [first]
            rlist.extend(
                [EquipmentRuntime(eq, rolename) for eq in eqlist
                    if eq.name != first.name])
            return rlist
        else:
            rlist = [EquipmentRuntime(eq, rolename) for eq in eqlist]
            if rlist:
                self._eqcache[rolename] = rlist[0]
                return rlist
            else:
                raise ConfigError("No equipment with role {} "
                                  "available in environment.".format(rolename))

    @property
    def supported_roles(self):
        return self._environment.get_supported_roles()

    def clear(self, delay=0):
        if self._eqcache:
            eqc = self._eqcache
            self._eqcache = {}
            while eqc:
                name, obj = eqc.popitem()
                try:
                    obj.clear()
                except:
                    logging.exception_error(
                        "environment clear: {!r}".format(obj))
        gc.collect()
        for obj in gc.garbage:
            try:
                obj.close()
            except:
                logging.exception_warning(
                    "environment garbage collect: {!r}".format(obj))
        del gc.garbage[:]
        if delay:
            scheduler.sleep(delay)

    def __getattr__(self, name):
        try:
            return self.get_role(name)
        except:
            ex, val, tb = sys.exc_info()
            raise AttributeError("{}: {}".format(ex.__name__, val))

    # Allow persistent storage of environment state in the state attribute.
    @property
    def state(self):
        return self._environment.get_attribute("state")

    @state.setter
    def state(self, newstate):
        self._environment.set_attribute("state", str(newstate))

    @state.deleter
    def state(self):
        self._environment.del_attribute("state")


class EquipmentModelRuntime:
    def __init__(self, equipmentmodel):
        d = {}
        d["name"] = equipmentmodel.name
        d["manufacturer"] = equipmentmodel.manufacturer.name
        for prop in equipmentmodel.attributes:
            d[prop.type.name] = prop.value
        self._attributes = d

    def __str__(self):
        return "{} {}".format(
            self._attributes["manufacturer"],
            self._attributes["name"])

    def __getitem__(self, name):
        return self._attributes[name]

    def get(self, name, default=None):
        return self._attributes.get(name, default)

    @property
    def name(self):
        return self._attributes["name"]


class EquipmentRuntime:

    def __init__(self, equipmentrow, rolename):
        self.name = equipmentrow.name
        self._equipment = equipmentrow
        self._controller = None
        self._init_controller = None
        d = {}
        d["hostname"] = equipmentrow.name
        d["modelname"] = equipmentrow.model.name
        d["manufacturer"] = equipmentrow.model.manufacturer.name
        d["role"] = rolename
        if equipmentrow.software:
            d["default_role"] = equipmentrow.software[0].category.name
        else:
            d["default_role"] = None
        # Specificly defined attributes may override the attributes above.
        for prop in equipmentrow.attributes:
            d[prop.type.name] = prop.value
        if equipmentrow.account:  # Account info takes precedence
            d["login"] = equipmentrow.account.login
            d["password"] = equipmentrow.account.password
        self._attributes = d
        self._equipmentmodel = EquipmentModelRuntime(equipmentrow.model)

    def clear(self):
        """Close any attached controllers.
        """
        if self._controller is not None:
            try:
                self._controller.close()
            except:
                logging.exception_warning(
                    "controller close: {!r}".format(self._controller))
            self._controller = None
        if self._init_controller is not None:
            try:
                self._init_controller.close()
            except:
                logging.exception_warning(
                    "Initial controller close: {!r}".format(
                        self._init_controller))
            self._init_controller = None

    @property
    def URL(self, scheme=None, port=None, path=None, with_account=False):
        """Construct a URL that can be used to access the equipment, if the
        equipment supports it.
        """
        attribs = self._attributes
        s = [scheme or attribs.get("serviceprotocol", "http")]
        s.append("://")
        if with_account:
            login = attribs.get("login")
            if login:
                pwd = attribs.get("password")
                if pwd:
                    s.append("%s:%s" % (login, pwd))
                else:
                    s.append(login)
                s.append("@")
        s.append(attribs["hostname"])
        port = attribs.get("serviceport", port)
        if port:
            s.append(":"); s.append(str(port))
        s.append(path or attribs.get("servicepath", "/"))
        return "".join(s)

    def __str__(self):
        return self._equipment.name

    def __getattr__(self, name):
        return getattr(self._equipment, name)

    def __getitem__(self, name):
        return self._attributes[name]

    def get(self, name, default=None):
        return self._attributes.get(name, default)

    @property
    def primary_interface(self):
        return self._equipment.interfaces[
            self._attributes.get("admin_interface", "eth0")]

    @property
    def controller(self):
        if self._init_controller is not None:
            self._init_controller = None
        if self._controller is None:
            self._controller = controller.get_controller(self,
                                                         self["accessmethod"])
        return self._controller

    @property
    def initial_controller(self):
        if self._init_controller is None:
            self._init_controller = controller.get_controller(
                self, self["initialaccessmethod"])
        return self._init_controller

    @property
    def state(self):
        return self._equipment.get_attribute("state")

    @state.setter
    def state(self, newstate):
        self._equipment.set_attribute("state", str(newstate))

    @state.deleter
    def state(self):
        self._equipment.del_attribute("state")

    @property
    def model(self):
        return self._equipmentmodel


def get_environment(name, storageurl=None):
    models.connect(storageurl)
    try:
        env = models.Environments.select().where(
            models.Environments.name == name).get()
    except models.DoesNotExist as err:
        raise ConfigError(
            "Bad environment name {!r}: {}".format(name, err)) from None
    return EnvironmentRuntime(env)

if __name__ == '__main__':
    env = get_environment("default")
    print(env)

