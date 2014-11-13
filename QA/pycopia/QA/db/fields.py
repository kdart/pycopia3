#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2014- Keith Dart <keith@dartworks.biz>
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
Custom peewee fields. These expose postgresql special types.
"""

import pickle
import ipaddress
from datetime import timedelta

from peewee import Field, DateTimeField, PostgresqlDatabase, SqliteDatabase


class DateTimeTZField(DateTimeField):
    """A datetime with timezone."""
    db_field = 'datetime_tz'


class IPv4Field(Field):
    """A field for an IP address that may be a host address."""
    db_field = 'inet'

    def db_value(self, value):
        return None if value is None else str(value)

    def python_value(self, value):
        return None if value is None else ipaddress.IPv4Interface(value)


class IPv6Field(Field):
    """A field for an IPv6 network address."""
    db_field = 'inet'

    def db_value(self, value):
        return None if value is None else str(value)

    def python_value(self, value):
        return None if value is None else ipaddress.IPv6Interface(value)


class CIDRField(Field):
    """A field for an IP network address."""
    db_field = 'cidr'

    def db_value(self, value):
        return None if value is None else str(value)

    def python_value(self, value):
        return None if value is None else ipaddress.IPv4Network(value)


class MACField(Field):
    """A field for an MAC layer address."""
    db_field = 'macaddr'

    def db_value(self, value):
        return None if value is None else str(value)

    def python_value(self, value):
        return None if value is None else MACAddress(value)


class PickleField(Field):
    """A field for an MAC layer address."""
    db_field = 'text'

    def db_value(self, value):
        return None if value is None else pickle.dumps(value)

    def python_value(self, value):
        return None if value is None else pickle.loads(value.encode("ascii"))



class IntervalField(Field):
    """Time intervals."""
    db_field = 'interval'

    def db_value(self, value):
        return None if value is None else "{} days {} seconds".format(value.days, value.seconds())

    def python_value(self, value):
        # 3 days 04:05:06
        if "days" in value:
            pass # TODO
        else:
            pass
        return None if value is None else timedelta(seconds=value)



class MACAddress:
    def __init__(self, mac):
        self.mac = str(mac)

    def __str__(self):
        return self.mac


PostgresqlDatabase.register_fields({
    'datetime_tz': 'timestamp with time zone',
    'macaddr': 'macaddr',
    'inet': 'inet',
    'cidr': 'cidr',
    'json': 'json',
})


SqliteDatabase.register_fields({
    "inet": "VARCHAR(32)", 
    "cidr": "VARCHAR(32)", 
    "macaddr": "VARCHAR(32)",
    'json': 'TEXT',
})

