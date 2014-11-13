#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 1999- Keith Dart <keith@kdart.com>
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
Collection of general purpose functions and objects that might be considered
general enough to be new built-ins.
"""

import sys
import codecs
from math import ceil


class NULLType(type):
    """Similar to None, but is also a no-op callable and empty iterable."""
    def __new__(cls, name, bases, dct):
        return type.__new__(cls, name, bases, dct)
    def __init__(cls, name, bases, dct):
        super(NULLType, cls).__init__(name, bases, dct)
    def __str__(self):
        return ""
    def __repr__(self):
        return "NULL"
    def __bool__(self):
        return False
    def __len__(self):
        return 0
    def __call__(self, *args, **kwargs):
        return None
    def __contains__(self, item):
        return False
    def __iter__(self):
        return self
    def __next__(*args):
        raise StopIteration
    def next(*args):
        raise StopIteration

NULL = NULLType("NULL", (type,), {})


class Enum(int):
    """A named number. Behaves as an integer, but produces a name when stringified."""
    def __new__(cls, val, name=None): # name must be optional for unpickling to work
        v = int.__new__(cls, val)
        v._name = str(name)
        return v
    def __getstate__(self):
        return int(self), self._name
    def __setstate__(self, args):
        i, self._name = args
    def __str__(self):
        return self._name
    def __repr__(self):
        return "{}({:d}, {!r})".format(self.__class__.__name__, self, self._name)
    def for_json(self):
        return {"_class_": "Enum", "_str_": self._name, "value": int(self)}


class Enums(list):
    """A list of Enum objects."""
    def __init__(self, *init, **kwinit):
        for i, val in enumerate(init):
            if issubclass(type(val), list):
                for j, subval in enumerate(val):
                    self.append(Enum(i+j, str(subval)))
            elif isinstance(val, Enum):
                self.append(val)
            else:
                self.append(Enum(i, str(val)))
        for name, value in list(kwinit.items()):
            enum = Enum(int(value), name)
            self.append(enum)
        self._mapping = None
        self.sort()

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, list.__repr__(self))

    @property
    def choices(self):
        return [(int(e), str(e)) for e in self]

    def find(self, value):
        """Find the Enum with the given value."""
        i = self.index(int(value))
        return self[i]

    def get_mapping(self):
        """Returns the enumerations as a dictionary with names as keys."""
        if self._mapping is None:
            d = dict([(str(it), it) for it in self])
            self._mapping = d
            return d
        else:
            return self._mapping

    def findstring(self, string):
        """Returns the Enum object given a name string."""
        d = self.get_mapping()
        try:
            return d[string]
        except KeyError:
            raise ValueError("Enum string not found.")


class sortedlist(list):
    """A list that maintains a sorted order when appended to."""
    def insort(self, x):
        hi = len(self)
        lo = 0
        while lo < hi:
            mid = (lo+hi)//2
            if x < self[mid]:
               hi = mid
            else:
               lo = mid+1
        self.insert(lo, x)
    append = insort

def sgn(val):
    """Sign function. Returns -1 if val negative, 0 if zero, and 1 if
    positive.
    """
    try:
        return val._sgn_()
    except AttributeError:
        if val == 0:
            return 0
        if val > 0:
            return 1
        else:
            return -1

# Nice floating point range function from Python snippets
def frange(limit1, limit2=None, increment=1.0):
  """
  Range function that accepts floats (and integers).

  >>> frange(-2, 2, 0.1)
  >>> frange(10)
  >>> frange(10, increment=0.5)

  The returned value is an iterator.  Use list(frange(...)) for a list.
  """
  if limit2 is None:
    limit2, limit1 = limit1, 0.
  else:
    limit1 = float(limit1)
  count = int(ceil((limit2 - limit1)/increment))
  return (limit1 + n*increment for n in range(0, count))


def debugmethod(meth):
    """Decorator for making methods enter the debugger on an exception."""
    def _lambda(*iargs, **ikwargs):
        try:
            return meth(*iargs, **ikwargs)
        except:
            ex, val, tb = sys.exc_info()
            from pycopia import debugger
            debugger.post_mortem(tb, ex, val)
    return _lambda


def systemcall(meth):
    """Decorator to make system call methods safe from interrupted system calls."""
    def systemcallmeth(*args, **kwargs):
        while 1:
            try:
                rv = meth(*args, **kwargs)
            except InterruptedError:
                continue
            else:
                break
        return rv
    return systemcallmeth


def removedups(s):
    """Return a list of the elements in s, but without duplicates.
    Thanks to Tim Peters for fast method.
    """
    n = len(s)
    if n == 0:
        return []
    u = {}
    try:
        for x in s:
            u[x] = 1
    except TypeError:
        del u  # move on to the next method
    else:
        return list(u.keys())
    # We can't hash all the elements.  Second fastest is to sort,
    # which brings the equal elements together; then duplicates are
    # easy to weed out in a single pass.
    try:
        t = list(s)
        t.sort()
    except TypeError:
        del t  # move on to the next method
    else:
        assert n > 0
        last = t[0]
        lasti = i = 1
        while i < n:
            if t[i] != last:
                t[lasti] = last = t[i]
                lasti = lasti + 1
            i = i + 1
        return t[:lasti]
    # Brute force is all that's left.
    u = []
    for x in s:
        if x not in u:
            u.append(x)
    return u


def reorder(datalist, indexlist):
    """reorder(datalist, indexlist)
    Returns a new list that is ordered according to the indexes in the
    indexlist.
    e.g.
    reorder(["a", "b", "c"], [2, 0, 1]) -> ["c", "a", "b"]
    """
    return [datalist[idx] for idx in indexlist]

def repeat(self,n, f):
    """Call function f, n times."""
    i = n
    while i > 0:
        f()
        i -= 1

def flatten(alist):
    """Flatten a nested set of lists into one list."""
    rv = []
    for val in alist:
        if isinstance(val, list):
            rv.extend(flatten(val))
        else:
            rv.append(val)
    return rv

def hexdigest(s):
    """Convert bytes to string of hexadecimal string for each character."""
    return codecs.encode(s, "hex").decode("ascii")

def unhexdigest(s):
    """Take a string of hexadecimal numbers and convert to binary string."""
    return bytes.fromhex(s)


