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


import os

from pycopia import logging

from pycopia.aid import NULL
from pycopia.dictlib import AttrDict
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
                raise AttributeError("RootContainer: No attribute or key "
                                     "'%s' found: %s" % (key, err))

    def __setattr__(self, key, obj):
        d = vars(self)
        if key in vars(self.__class__):
            type.__setattr__(self.__class__, key, obj)
        elif key in d:  # existing local attribute
            d[key] = obj
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
            gb = dict(self.items())
            exec(compile(
                open(filename).read(), filename, 'exec'), gb, self._cache)

    # Updates done from external dicts only update the local cache. If you
    # want it persistent, enter it into the persistent store another way.
    def update(self, other):
        for k, v in list(other.items()):
            d = self._cache
            path = k.split(".")  # allows for keys with dot-path
            for part in path[:-1]:
                d = d[part]
            # Use setattr for the sake of attribute-dicts, properties, and
            # other objects.
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
        path = k.split(".")  # allows for keys with dot-path
        for part in path[:-1]:
            d = d[part]
        # Use setattr for attribute-dicts, properties, and other objects.
        setattr(d, path[-1], v)

    def evalupdate(self, other):
        for k, v in other.items():
            self.evalset(k, v)

    def get_account(self, identifier):
        """Get account credentials by identifier."""
        AID = models.AccountIds
        try:
            acct = AID.select().where(AID.identifier == identifier).get()
        except models.DoesNotExist as err:
            raise ConfigError(
                "Bad account identifier {!r}: {!s}".format(identifier, err))
        return acct.login, acct.password


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


def get_config(storageurl=None, _extrafiles=None, initdict=None, **kwargs):
    """Get primary configuration.

    Returns a RootContainer instance containing configuration parameters.  An
    extra dictionary may be merged in with the 'initdict' parameter.  And
    finally, extra options may be added with keyword parameters when calling
    this.
    """
    models.connect(storageurl)
    files = []

    if type(_extrafiles) is str:
        _extrafiles = [_extrafiles]
    if _extrafiles:
        files.extend(_extrafiles)
    try:
        rootnode = config.get_root()
    except models.OperationalError:
        logging.exception_warning(
            "Could not connect to database. Configuration not available.")
        return get_mock_config(files, initdict, kwargs)
    cache = AttrDict()
    flags = AttrDict()
    # copy flag values to cache so changes don't persist.
    flagsnode = Config.select().where(
        (Config.parent == rootnode) & (Config.name == "flags")).get()
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


