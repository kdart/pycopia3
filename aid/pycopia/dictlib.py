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
Extra dictionary subclasses.

"""

class AttrDict(dict):
    """A dictionary with attribute-style access. It maps attribute access to
    the real dictionary.  """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

    def __getstate__(self):
        return list(vars(self).items())

    def __setstate__(self, items):
        d = vars(self)
        for key, val in items:
            d[key] = val

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, dict.__repr__(self))

    def __setitem__(self, key, value):
        return super(AttrDict, self).__setitem__(key, value)

    def __getitem__(self, name):
        return super(AttrDict, self).__getitem__(name)

    def __delitem__(self, name):
        return super(AttrDict, self).__delitem__(name)

    __getattr__ = __getitem__
    __setattr__ = __setitem__

    def copy(self):
        return AttrDict(self)

    def evalset(self, k, v):
        """Evaluates the (string) value to convert it to an object before adding.

        Useful for specifying objects from string-sources, such
        as the command line.
        """
        if type(v) is str:
            try:
                v = eval(v, {}, vars(self))
            except:
                pass
        d = self
        path = k.split(".") # allows for keys with dot-path in nested dictionaries.
        for part in path[:-1]:
            d = d[part]
        # Use setattr for attribute-dicts, properties, and other objects.
        setattr(d, path[-1], v)

    def evalupdate(self, other):
        for k, v in other.items():
            self.evalset(k, v)


class AttrDictDefault(dict):
    """A dictionary with attribute-style access. It maps attribute access to
    the real dictionary. Returns a default entry if key is not found. """
    def __init__(self, init={}, default=None):
        dict.__init__(self, init)
        self.__dict__["_default"] = default

    def __getstate__(self):
        return list(self.__dict__.items())

    def __setstate__(self, items):
        for key, val in items:
            self.__dict__[key] = val

    def __repr__(self):
        return "%s(%s, %r)" % (self.__class__.__name__, dict.__repr__(self),
            self.__dict__["_default"])

    def __setitem__(self, key, value):
        return super(AttrDictDefault, self).__setitem__(key, value)

    def __getitem__(self, name):
        try:
            return super(AttrDictDefault, self).__getitem__(name)
        except KeyError:
            return self.__dict__["_default"]

    def __delitem__(self, name):
        return super(AttrDictDefault, self).__delitem__(name)

    __getattr__ = __getitem__
    __setattr__ = __setitem__

    def copy(self):
        return self.__class__(self, self.__dict__["_default"])

    def get(self, default=None):
        df = default or self.__dict__["_default"]
        return super(AttrDictDefault, self).get(name, df)

