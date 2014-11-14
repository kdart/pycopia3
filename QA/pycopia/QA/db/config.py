#!/usr/bin/python2.7
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2012  Keith Dart <keith@kdart.com>
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

Pycopia Configuration and Information storage
---------------------------------------------

Wrap the Config table in the database and make it look like a tree of
name-value pairs (mappings).

Values are serialized Python objects (pickles). So you can have arbitrary data
structures as values. In theory you can add object instances as well, but this
should be avoided.

The NULL object (from pycopia.aid) as value is used as a sentinal to signal a
"directory", or container node. It should not be a value.

Containers can be owned by a user. New containers created by a user are owned
by the same user. If a user with flag superuser creates a new container it is
not owned by anybody (set the ownership as a separate operation). A superuser can
see all containers, but non-superuser users only see their own containers.  New
containers created without a registered user inherit ownership from parent
node.

"""





import re

from pycopia.QA.db import models
from pycopia.QA.exceptions import ConfigError
# The NULL value is used to flag a container node.
from pycopia.aid import NULL

Config = models.Config



def get_root():
    c = Config.select().filter(
            (Config.name=="root") & (Config.parent==None)).get()
    return c


class Container:
    """Make a relational table quack like a nested dictionary."""
    def __init__(self, configrow, user=None, testcase=None):
        d = vars(self)
        d["node"] = configrow
        d["_user"] = user
        d["_testcase"] = testcase

    def __str__(self):
        if self.node.value is NULL:
            s = []
            for ch in self.node.children:
                s.append(str(ch))
            return "(%s: %s)" % (self.node.name, ", ".join(s))
        else:
            return str(self.node)

    def __setitem__(self, name, value):
        pass

    def __getitem__(self, name):
        try:
            item = Config.select().filter((Config.parent==self.node) & (Config.name==name)).get()
            if item.value is NULL:
                return Container(item, user=self._user, testcase=self._testcase)
            else:
                return item.value
        except models.DoesNotExist as err:
            raise KeyError(
                    "Container: No item {!r} found: {!s}".format(name, err))

    def __delitem__(self, name):
        pass

    @property
    def value(self):
        return self.node.value

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default

    def keys(self):
        #for item in Config.select().where((Config.parent==self.node) & (Config.value % NULL)):
        for item in Config.select().where(Config.parent==self.node):
            yield item.name

    def items(self):
        for cf in Config.select(Config.name, Config.value).where(Config.parent==self.node):
            yield cf.name, cf.value

    def values(self):
        for item in Config.select().where(Config.parent==self.node):
            yield item.value

    def add_container(self, name):
        me = self.node
        if me.value is NULL:
            pass # TODO
        else:
            raise ConfigError("Cannot add container to value pair.")

    def get_container(self, name):
        pass
        c = XXX
        if c.value is NULL:
            return Container(c, user=self._user, testcase=self._testcase)
        else:
            raise ConfigError("Container {} not found.".format(name))

    def __contains__(self, key):
        return key in self

    def __iter__(self):
        pass
        #me = self.node
        return self

    def __next__(self):
        pass
    next = __next__

    def __getattribute__(self, key):
        try:
            return super(Container, self).__getattribute__(key)
        except AttributeError:
            d = vars(self)
            node = d["node"]
            try:
                item = Config.select().filter((Config.parent==node) & (Config.name==key)).get()
                if item.value is NULL:
                    return Container(item, user=self._user, testcase=self._testcase)
                else:
                    return item.value
            except models.DoesNotExist as err:
                raise AttributeError(
                        "Container: No attribute or key {!r} found: {!s}".format(key, err))

    def __setattr__(self, key, obj):
        if key in vars(self.__class__): # to force property access
            type.__setattr__(self.__class__, key, obj)
        elif key in vars(self): # existing local attribute
            vars(self)[key] =  obj
        else:
            self.__setitem__(key, obj)

    def __delattr__(self, key):
        try:
            self.__delitem__(key)
        except KeyError:
            object.__delattr__(self, key)

    def has_key(self, key):
        me = self.node
        pass
        #return q.count() > 0

    _var_re = re.compile(br'\$([a-zA-Z0-9_\?]+|\{[^}]*\})')

    # perform shell-like variable expansion
    def expand(self, value):
        if '$' not in value:
            return value
        i = 0
        while 1:
            m = Container._var_re.search(value, i)
            if not m:
                return value
            i, j = m.span(0)
            oname = vname = m.group(1)
            if vname.startswith('{') and vname.endswith('}'):
                vname = vname[1:-1]
            tail = value[j:]
            value = value[:i] + str(self.get(vname, "$"+oname))
            i = len(value)
            value += tail

    def expand_params(self, tup):
        rv = []
        for arg in tup:
            if isinstance(arg, str):
                rv.append(self.expand(arg))
            else:
                rv.append(arg)
        return tuple(rv)

    def set_owner(self, user):
        if self._user is not None and self._user.is_superuser:
            if self.node.parent is not None:
                self.node.set_owner(user)
            else:
                raise ConfigError("Root container can't be owned.")
        else:
            raise ConfigError("Current user must be superuser to change ownership.")


def get_item(node, name):
    return Config.select().where((Config.parent==node) & (Config.name==name)).get()


# entry point for basic configuration model.
def get_config():
    root = get_root()
    return Container(root)


if __name__ == "__main__":
    from pycopia import autodebug
    models.connect('postgresql://pycopia@localhost/pycopia')
    #r = get_root()
    #print(r)
    #print(r.get_child("flags"))
    cf = get_config()
