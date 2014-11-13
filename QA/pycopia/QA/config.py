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
Configuration and Information storage
-------------------------------------

Provides runtime wrappers for persistent (database) objects with
extra methods for constructing active controllers.
"""


import sys, os, gc

from pycopia import logging

from pycopia.aid import NULL
from pycopia import scheduler
from pycopia.dictlib import AttrDict
from pycopia.QA import controller
from pycopia.QA.exceptions import ConfigError

from pycopia.QA.db import models
from pycopia.QA.db import config

Config = models.Config


class RootContainer(config.Container):
    """RootContainer is the primary configuration holder.

    The root container is special. It contains special object
    constructor methods, and a local writeable cache. It also supports
    path access using the dot as path separator.
    """

    def __init__(self, container, cache):
        super(RootContainer, self).__init__(container)
        vars(self)["_cache"] = cache
        # cacheable objects
        cache._environment = None
        cache._UI = None

    def __repr__(self):
        return "<RootContainer>"

    def __getattribute__(self, key):
        if key == "__dict__":
            return object.__getattribute__(self, key)
        try:
            # check the local cache first, overrides persistent storage
            return vars(self)["_cache"].__getitem__(key)
        except KeyError:
            pass
        try:
            return super(RootContainer, self).__getattribute__(key)
        except AttributeError:
            d = vars(self)
            node = d["node"]
            try:
                item = config.get_item(node, key)
                if item.value is NULL:
                    return config.Container(item)
                else:
                    return item.value
            except models.DoesNotExist as err:
                raise AttributeError("RootContainer: No attribute or key '%s' found: %s" % (key, err))

    def __setattr__(self, key, obj):
        d = vars(self)
        if key in vars(self.__class__):
            type.__setattr__(self.__class__, key, obj)
        elif key in d: # existing local attribute
            d[key] =  obj
        else:
            d["_cache"].__setitem__(key, obj)

    def __delattr__(self, key):
        try:
            vars(self)["_cache"].__delitem__(key)
        except KeyError:
            object.__delattr__(self, key)

    def __getitem__(self, key):
        try:
            return getattr(self._cache, key)
        except (AttributeError, KeyError, NameError):
            return super(RootContainer, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key in self._cache:
            self._cache[key] = value
        else:
            return super(RootContainer, self).__setitem__(key, value)

    def __delitem__(self, key):
        try:
            del self._cache[key]
        except KeyError:
            super(RootContainer, self).__delitem__(key)

    def get(self, key, default=None):
        try:
            rv = self.__getitem__(key)
        except KeyError:
            rv = default
        return rv

    def has_key(self, key):
        return key in self._cache or key in super(RootContainer, self)

    def copy(self):
        return self.__class__(self.node, self._cache.copy())

    # files update the local cache only.
    def mergefile(self, filename):
        if os.path.isfile(filename):
            gb = dict(list(self.items()))
            exec(compile(open(filename).read(), filename, 'exec'), gb, self._cache)

    # Updates done from external dicts only update the local cache. If you
    # want it persistent, enter it into the persistent store another way.
    def update(self, other):
        for k, v in list(other.items()):
            d = self._cache
            path = k.split(".") # allows for keys with dot-path
            for part in path[:-1]:
                d = d[part]
            # Use setattr for the sake of attribute-dicts, properties, and other objects.
            setattr(d, path[-1], v)

    def setdefault(self, key, val):
        d = self._cache
        path = key.split(".")
        for part in path[:-1]:
            d = d[part]
        return d.setdefault(path[-1], val)

    def evalset(self, k, v):
        """Evaluates the (string) value to convert it to an object in the
        storage first. Useful for specifying objects from string-sources, such
        as the command line. """
        if type(v) is str:
            try:
                v = eval(v, {}, vars(self))
            except:
                pass
        d = self._cache
        path = k.split(".") # allows for keys with dot-path
        for part in path[:-1]:
            d = d[part]
        # Use setattr for attribute-dicts, properties, and other objects.
        setattr(d, path[-1], v)

    def evalupdate(self, other):
        for k, v in other.items():
            self.evalset(k, v)

    @property
    def environment(self):
        if self._cache.get("_environment") is None:
# TODO factor out
            name = self.get("environmentname", "default")
            if name:
                try:
                    env = models.Environment.select().where(models.Environment.name==name).get()
                except models.DoesNotExist as err:
                    raise ConfigError("Bad environmentname %r: %s" % (name, err))
                #username = self.get("username") # username should be set by test runner
                #if username:
                #    if env.is_owned():
                #        if env.owner.username != username:
                #            raise ConfigError("Environment is currently owned by: %s" % (env.owner,))
                #    env.set_owner_by_username(db, username)

                env = EnvironmentRuntime(env)
                self._cache["_environment"] = env
            else:
                raise ConfigError("Bad environmentname {!r}.".format(name))
        return self._cache["_environment"]

    def _del_environment(self):
        envruntime = self._cache.get("_environment")
        if envruntime is not None:
            self._cache["_environment"] = None
            envruntime._environment.clear_owner()
            del envruntime._environment

    @property
    def UI(self):
        if self._cache.get("_UI") is None:
            ui = self._build_userinterface()
            self._cache["_UI"] = ui
            return ui
        else:
            return self._cache["_UI"]

    def _build_userinterface(self):
        from pycopia import UI
        uitype = self.get("userinterfacetype", "default")
        params = self.userinterfaces.get(uitype)
        if params:
            params = self.expand_params(params)
        else:
            params = self.userinterfaces.get("default")
        return UI.get_userinterface(*params)

    def get_account(self, identifier):
        """Get account credentials by identifier."""
        AID = models.AccountIds
        try:
            acct = AID.select().where(AID.identifier==identifier).get()
        except models.DoesNotExist as err:
            raise ConfigError("Bad account identifier {!r}: {!s}".format(identifier, err))
        return acct.login, acct.password

    def get_equipment(self, name, role="unspecified"):
        """Get any equipment runtime from the configuration by name."""
        try:
            eqrow = models.Equipment.select().where(models.Equipment.name.contains(name)).get()
        except models.DoesNotExist as err:
            raise ConfigError("Bad equipment name {!r}: {!s}".format(name, err))
        return EquipmentRuntime(eqrow, role)



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
            rlist.extend([EquipmentRuntime(eq, rolename) for eq in eqlist if eq.name != first.name])
            return rlist
        else:
            rlist = [EquipmentRuntime(eq, rolename) for eq in eqlist]
            if rlist:
                self._eqcache[rolename] = rlist[0]
                return rlist
            else:
                raise ConfigError("No equipment with role {} available in environment.".format(rolename))

    @property
    def supported_roles(self):
        return self._environment.get_supported_roles()

    def clear(self):
        if self._eqcache:
            eqc = self._eqcache
            self._eqcache = {}
            while eqc:
                name, obj = eqc.popitem()
                try:
                    obj.clear()
                except:
                    logging.exception_error("environment clear: {!r}".format(obj))
        gc.collect()
        for obj in gc.garbage:
            try:
                obj.close()
            except:
                logging.exception_warning("environment garbage collect: {!r}".format(obj))
        del gc.garbage[:]
        scheduler.sleep(2) # some devices need time to fully clear or disconnect

    def __getattr__(self, name):
        try:
            return self.get_role(name)
        except:
            ex, val, tb = sys.exc_info()
            raise AttributeError("%s: %s" % (ex, val))

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
        return "{} {}".format(self._attributes["manufacturer"], self._attributes["name"])

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
        for prop in equipmentrow.attributes: # These may override the attributes above.
            d[prop.type.name] = prop.value
        if equipmentrow.account: # Account info takes precedence
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
                logging.exception_warning("controller close: {!r}".format(self._controller))
            self._controller = None
        if self._init_controller is not None:
            try:
                self._init_controller.close()
            except:
                logging.exception_warning("initial controller close: {!r}".format(self._init_controller))
            self._init_controller = None

    @property
    def URL(self, scheme=None, port=None, path=None, with_account=False):
        """Construct a URL that can be used to access the equipment, if the equipment supports it.
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
            s.append(":") ; s.append(str(port))
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
        return self._equipment.interfaces[self._attributes.get("admin_interface", "eth0")]

    @property
    def controller(self):
        if self._init_controller is not None:
            self._init_controller = None
        if self._controller is None:
            self._controller = controller.get_controller(
                    self,
                    self["accessmethod"])
        return self._controller

    @property
    def initial_controller(self):
        if self._init_controller is None:
            self._init_controller = controller.get_controller(
                    self,
                    self["initialaccessmethod"])
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


def get_mock_config(filelist=None, initdict=None, kwargs=None):
    flags = AttrDict()
    flags.DEBUG = 0
    flags.VERBOSE = 0
    cf = AttrDict()
    cf.flags = flags
    if filelist:
        for f in filelist:
            if os.path.isfile(f):
                gb = globals()
                exec(compile(open(f).read(), f, 'exec'), gb, cf)
    if type(initdict) is dict:
        cf.update(initdict)
    if type(kwargs) is dict:
        cf.update(kwargs)
    return cf

def get_config(_extrafiles=None, initdict=None, **kwargs):
    """Get primary configuration.

    Returns a RootContainer instance containing configuration parameters.
    An extra dictionary may be merged in with the 'initdict' parameter.
    And finally, extra options may be added with keyword parameters when calling
    this.
    """
    models.connect()
    files = []

    if type(_extrafiles) is str:
        _extrafiles = [_extrafiles]
    if _extrafiles:
        files.extend(_extrafiles)
    try:
        rootnode = config.get_root()
    except models.OperationalError:
        logging.exception_warning("Could not connect to database. Configuration not available.")
        return get_mock_config(files, initdict, kwargs)
    cache = AttrDict()
    flags = AttrDict()
    # copy flag values to cache so changes don't persist.
    flagsnode = Config.select().where((Config.parent==rootnode) & (Config.name=="flags")).get()
    for valnode in flagsnode.children:
        flags[valnode.name] = valnode.value
    cache.flags = flags
    cf = RootContainer(rootnode, cache)
    for f in files:
        if os.path.isfile(f):
            cf.mergefile(f)
    if type(initdict) is dict:
        cf.evalupdate(initdict)
    cf.update(kwargs)
    return cf


if __name__ == "__main__":
    from pycopia import autodebug
    cf = get_config()
    print(cf)
    print(cf.flags)
    print(cf.flags.DEBUG)
    #cf.environmentname = "default"
   #env = cf._get_environment()
#    env = cf.environment
#    print("Environment:")
#    print(env)
#    print("Supported roles:")
#    print(env.get_supported_roles())
##    print env.get_role("testcontroller")
#    #print env._get_DUT()
#    #dut = env.DUT
#    #print dut["default_role"]
#    print(cf.environment._environment.owner)
#    del cf.environment


