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
Data model for QA framework. May also serve a base for lab management, since it
contains complete information about all equipment and networks.
"""

from datetime import datetime
from hashlib import sha1
from urllib import parse as urlparse

from pytz import timezone
from peewee import *  # noqa

from pycopia import basicconfig
from pycopia import logging
from pycopia.aid import hexdigest, unhexdigest, NULL
from pycopia.QA.exceptions import (ModelError, ModelAttributeError,
                                   ModelValidationError)
from pycopia.QA import constants

from pycopia.QA.db.fields import *  # noqa


# Every table a QA framework could ever want. ;)
TABLES = ['AccountIds', 'CountryCodes', 'Addresses', 'AttributeType', 'User',
          'UserMessage', 'AuthGroup', 'AuthPermission', 'Contacts',
          'Corporations', 'EquipmentModel', 'Location', 'LanguageCodes',
          'Equipment', 'ClientSession', 'Components', 'ProjectCategory',
          'Projects', 'TestSuites', 'RequirementRef', 'TestCases', 'Config',
          'CorpAttributeType', 'FunctionalArea', 'EnvironmentAttributeType',
          'Environments', 'Function', 'Software', 'InterfaceType', 'Networks',
          'Interfaces', 'LanguageSets', 'ProjectVersions', 'RiskCategory',
          'RiskFactors', 'Schedule', 'SoftwareVariant', 'TestJobs',
          'TestResults', 'TestResultsData', 'Testequipment', 'UseCases', ]

__all__ = TABLES + ['time_now', 'coerce_value_type', 'get_columns',
                    'get_foreign_keys', 'get_metadata', 'get_column_metadata',
                    'get_rowdisplay', 'get_primary_key_name',
                    'get_primary_key_value', 'get_tables', 'connect']


UTC = timezone('UTC')
_SECRET_KEY = None


def time_now():
    """Return datetime right now, as UTC."""
    return datetime.now(UTC)

database_proxy = Proxy()
database = None


class BaseModel(Model):
    class Meta:
        database = database_proxy


class AccountIds(BaseModel):
    identifier = CharField(max_length=80)
    login = CharField(max_length=80, null=True)
    note = TextField(null=True)
    password = CharField(max_length=80, null=True)

    class Meta:
        db_table = 'account_ids'
        indexes = (
            (("identifier",), True),
        )


class CountryCodes(BaseModel):
    isocode = CharField(max_length=4, unique=True)
    name = CharField(max_length=80)

    class Meta:
        db_table = 'country_codes'


class Addresses(BaseModel):
    address = TextField()
    address2 = TextField(null=True)
    city = CharField(max_length=80, null=True)
    stateprov = CharField(max_length=80, null=True)
    country = ForeignKeyField(db_column='country_id', null=True,
                              rel_model=CountryCodes, to_field='id')
    postalcode = CharField(max_length=15, null=True)

    class Meta:
        db_table = 'addresses'


class AttributeType(BaseModel):
    name = CharField(max_length=80, unique=True)
    description = TextField(null=True)
    value_type = EnumField(constants.ValueType)

    class Meta:
        db_table = 'attribute_type'

    @classmethod
    def get_by_name(cls, name):
        try:
            attrtype = cls.select().where(cls.name == str(name)).get()
        except DoesNotExist:
            raise ModelAttributeError(
                "No attribute type {!r} defined.".format(name))
        return attrtype

    @classmethod
    def get_attribute_list(cls):
        return cls.select(cls.name, cls.value_type).tuples()


class User(BaseModel):
    ROW_DISPLAY = ("username", "first_name", "last_name", "email")
    username = CharField(max_length=30, unique=True)
    first_name = CharField(max_length=30)
    middle_name = CharField(max_length=30, null=True)
    last_name = CharField(max_length=30)
    address = ForeignKeyField(db_column='address_id', null=True,
                              rel_model=Addresses, to_field='id')
    _password = CharField(db_column="password", max_length=40, null=True)
    authservice = CharField(max_length=20)
    last_login = DateTimeTZField(default=time_now)
    date_joined = DateTimeTZField(default=time_now)
    email = CharField(max_length=75, null=True)
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=True)
    is_superuser = BooleanField(default=False)

    class Meta:
        db_table = 'auth_user'

    def __str__(self):
        return "%s %s (%s)" % (self.first_name, self.last_name, self.username)

    def __repr__(self):
        return "User(username={!r}, first_name={!r}, last_name={!r})".format(
            self.username, self.first_name, self.last_name)

    @property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    def set_last_login(self):
            self.last_login = time_now()

    @property
    def groups(self):
        return list(_AuthUserGroups.select().filter(_AuthUserGroups.user == self))
        #EA = _EquipmentAttributes
        #try:
        #    ea = EA.select().where(
        #        (EA.equipment == self) & (EA.type == attrtype)).get()
        #except DoesNotExist:
        #    raise ModelAttributeError(
        #        "No attribute {!r} set.".format(attrname))
        #return ea.value

    @groups.setter
    def groups(self, usergroup):
        self.group_add(usergroup)

    @groups.deleter
    def groups(self, usergroup):
        pass

    def group_add(self, usergroup):
        if not isinstance(usergroup, (list, tuple)):
            usergroup = [usergroup]
        inserts = [{"user": self, "group": grp} for grp in usergroup]
        _AuthUserGroups.insert_many(inserts).execute()

    # Passwords are stored in the database encrypted.
    @property
    def password(self):
        from Crypto.Cipher import AES
        eng = AES.new(_get_key(), AES.MODE_ECB)
        return eng.decrypt(unhexdigest(
            self._password)).strip(b"\0").decode("utf8")

    @password.setter
    def password(self, passwd):
        # Using pycrypto package.
        from Crypto.Cipher import AES
        eng = AES.new(_get_key(), AES.MODE_ECB)
        passwd = passwd[:16].encode("utf-8")
        self._password = hexdigest(
            eng.encrypt((passwd + b"\0"*(16 - len(passwd)))[:16]))

    def get_session_key(self):
        h = sha1()
        h.update(str(self.id))
        h.update(self.username)
        h.update(str(self.last_login))
        return h.hexdigest()

    @classmethod
    def get_by_username(cls, username):
        return cls.select().filter(cls.username == username).first()


def _get_secret():
    global _SECRET_KEY
    try:
        cf = basicconfig.get_config("auth.conf")
    except basicconfig.ConfigReadError:
        logging.warn(
            "User encryption key not found for auth app, using default.")
        _SECRET_KEY = b"Testkey"
    else:
        _SECRET_KEY = cf.SECRET_KEY.encode("utf-8")


def _get_key():
    global _SECRET_KEY, _get_secret
    if _SECRET_KEY is None:
        _get_secret()
        del _get_secret
        h = sha1()
        h.update(_SECRET_KEY)
        h.update(b"ifucnrdthsurtoocls")
        _SECRET_KEY = h.digest()[:16]
    return _SECRET_KEY


class UserMessage(BaseModel):
    user = ForeignKeyField(db_column='user_id', rel_model=User, to_field='id',
                           related_name="messages",
                           on_update="CASCADE", on_delete="CASCADE")
    message = TextField()

    class Meta:
        db_table = 'user_message'


# Permissions
class AuthGroup(BaseModel):
    name = CharField(max_length=80, unique=True)
    description = TextField(null=True)

    class Meta:
        db_table = 'auth_group'


class AuthPermission(BaseModel):
    name = CharField(max_length=50, unique=True)
    description = TextField(null=True)

    class Meta:
        db_table = 'auth_permission'


class _AuthGroupPermissions(BaseModel):
    group = ForeignKeyField(db_column='group_id',
                            rel_model=AuthGroup, to_field='id')
    permission = ForeignKeyField(db_column='permission_id',
                                 rel_model=AuthPermission, to_field='id',
                                 related_name="groups")

    class Meta:
        db_table = 'auth_group_permissions'
        primary_key = CompositeKey('group', 'permission')


class _AuthUserUserPermissions(BaseModel):
    user = ForeignKeyField(db_column='user_id', rel_model=User, to_field='id',
                           related_name="permissions",
                           on_update="CASCADE", on_delete="CASCADE")
    permission = ForeignKeyField(db_column='permission_id',
                                 rel_model=AuthPermission,
                                 to_field='id', related_name="users")

    class Meta:
        db_table = 'auth_user_user_permissions'
        primary_key = CompositeKey('user', 'permission')


class _AuthUserGroups(BaseModel):
    user = ForeignKeyField(db_column='user_id', rel_model=User, to_field='id',
                           related_name="_groups",
                           on_update="CASCADE", on_delete="CASCADE")
    group = ForeignKeyField(db_column='group_id',
                            rel_model=AuthGroup, to_field='id')

    class Meta:
        db_table = 'auth_user_groups'
        primary_key = CompositeKey('user', 'group')


class Contacts(BaseModel):
    lastname = CharField(max_length=50)
    middlename = CharField(max_length=50, null=True)
    firstname = CharField(max_length=50)
    prefix = CharField(max_length=15, null=True)
    title = CharField(max_length=50, null=True)
    position = CharField(max_length=100, null=True)
    email = CharField(max_length=80, null=True)
    note = TextField(null=True)
    phonehome = CharField(max_length=25, null=True)
    phonemobile = CharField(max_length=25, null=True)
    phoneoffice = CharField(max_length=25, null=True)
    phoneother = CharField(max_length=25, null=True)
    phonework = CharField(max_length=25, null=True)
    pager = CharField(max_length=25, null=True)
    fax = CharField(max_length=25, null=True)
    address = ForeignKeyField(db_column='address_id', null=True,
                              rel_model=Addresses, to_field='id')
    user = ForeignKeyField(db_column='user_id', null=True,
                           rel_model=User, to_field='id',
                           related_name="contacts",
                           on_update="CASCADE", on_delete="SET NULL")

    class Meta:
        db_table = 'contacts'
        indexes = (
            (("lastname",), False),
            )


class Corporations(BaseModel):
    name = CharField(max_length=255)
    address = ForeignKeyField(db_column='address_id', null=True,
                              rel_model=Addresses, to_field='id')
    contact = ForeignKeyField(db_column='contact_id', null=True,
                              rel_model=Contacts, to_field='id',
                              related_name="corporations")
    country = ForeignKeyField(db_column='country_id', null=True,
                              rel_model=CountryCodes, to_field='id')
    notes = TextField(null=True)
    parent = ForeignKeyField(db_column='parent_id', null=True,
                             rel_model='self', to_field='id')

    class Meta:
        db_table = 'corporations'
        indexes = (
            (("name",), False),
            )

    def __str__(self):
        return self.name


class EquipmentModel(BaseModel):
    ROW_DISPLAY = ("manufacturer", "name")
    manufacturer = ForeignKeyField(db_column='manufacturer_id',
                                   rel_model=Corporations, to_field='id',
                                   related_name="products")
    name = CharField(max_length=255)
    note = TextField(null=True)
    picture = CharField(max_length=255, null=True)
    specs = CharField(max_length=255, null=True)
    rackunits = IntegerField(null=True)

    class Meta:
        db_table = 'equipment_model'
        indexes = (
            (("name", "manufacturer"), True),
            )

    def __str__(self):
        return self.name

    def update_attribute(self, attrname, value):
        attrtype = AttributeType.get_by_name(attrname)
        EMA = _EquipmentModelAttributes
        try:
            existing = EMA.select().where(
                (EMA.equipmentmodel == self) & (EMA.type == attrtype)).get()
        except DoesNotExist:
            self.set_attribute(attrname, value)
        else:
            with database.atomic():
                existing.value = coerce_value_type(attrtype.value_type, value)

    def set_attribute(self, attrname, value):
        attrtype = AttributeType.get_by_name(attrname)
        value = coerce_value_type(attrtype.value_type, value)
        with database.atomic():
            _EquipmentModelAttributes(equipmentmodel=self, type=attrtype,
                                      value=value)

    def get_attribute(self, attrname):
        attrtype = AttributeType.get_by_name(attrname)
        EMA = _EquipmentModelAttributes
        try:
            ea = EMA.select().where(
                (EMA.equipmentmodel == self) & (EMA.type == attrtype)).get()
        except DoesNotExist:
            raise ModelAttributeError(
                "No attribute {!r} set.".format(attrname))
        return ea.value

    def del_attribute(self, attrtype):
        attrtype = AttributeType.get_by_name(attrname)
        EMA = _EquipmentModelAttributes
        try:
            ea = EMA.select().where(
                (EMA.equipmentmodel == self) & (EMA.type == attrtype)).get()
        except DoesNotExist:
            pass
        else:
            with database.atomic():
                ea.delete_instance()


class Location(BaseModel):
    address = ForeignKeyField(db_column='address_id', null=True,
                              rel_model=Addresses, to_field='id')
    contact = ForeignKeyField(db_column='contact_id', null=True,
                              rel_model=Contacts, to_field='id',
                              related_name="locations",
                              on_update="CASCADE", on_delete="SET NULL")
    locationcode = CharField(max_length=80)

    class Meta:
        db_table = 'location'


class LanguageCodes(BaseModel):
    name = CharField(max_length=80, unique=True)
    isocode = CharField(max_length=6, unique=True)

    class Meta:
        db_table = 'language_codes'


class Equipment(BaseModel):
    ROW_DISPLAY = ("name", "model", "serno")

    name = CharField(max_length=255, unique=True)
    serno = CharField(max_length=255, null=True)
    model = ForeignKeyField(db_column='model_id',
                            rel_model=EquipmentModel, to_field='id',
                            related_name="equipment")
    account = ForeignKeyField(db_column='account_id', null=True,
                              rel_model=AccountIds, to_field='id')
    addeddate = DateTimeTZField(null=True, default=time_now)
    location = ForeignKeyField(db_column='location_id', null=True,
                               rel_model=Location, to_field='id',
                               related_name="equipment")
    sublocation = TextField(null=True)
    owner = ForeignKeyField(db_column='owner_id', null=True,
                            rel_model=User, to_field='id',
                            related_name="equipment",
                            on_update="CASCADE", on_delete="SET NULL")
    parent = ForeignKeyField(db_column='parent_id', null=True,
                             rel_model='self', to_field='id')
    vendor = ForeignKeyField(db_column='vendor_id', null=True,
                             rel_model=Corporations, to_field='id',
                             related_name="vended")
    language = ForeignKeyField(db_column='language_id', null=True,
                               rel_model=LanguageCodes, to_field='id',
                               related_name="equipment")
    comments = TextField(null=True)
    active = BooleanField(default=True)

    class Meta:
        db_table = 'equipment'

    def __str__(self):
        return self.name

    def update_attribute(self, attrname, value):
        attrtype = AttributeType.get_by_name(attrname)
        EA = _EquipmentAttributes
        try:
            existing = EA.select().where(
                (EA.equipment == self) & (EA.type == attrtype)).get()
        except DoesNotExist:
            self.set_attribute(attrname, value)
        else:
            with database.atomic():
                existing.value = coerce_value_type(attrtype.value_type, value)

    def set_attribute(self, attrname, value):
        attrtype = AttributeType.get_by_name(attrname)
        value = coerce_value_type(attrtype.value_type, value)
        with database.atomic():
            _EquipmentAttributes.create(equipment=self,
                                        type=attrtype, value=value)

    def get_attribute(self, attrname):
        attrtype = AttributeType.get_by_name(attrname)
        EA = _EquipmentAttributes
        try:
            ea = EA.select().where(
                (EA.equipment == self) & (EA.type == attrtype)).get()
        except DoesNotExist:
            raise ModelAttributeError(
                "No attribute {!r} set.".format(attrname))
        return ea.value

    def del_attribute(self, attrname):
        attrtype = AttributeType.get_by_name(attrname)
        EA = _EquipmentAttributes
        try:
            ea = EA.select().where(
                (EA.equipment == self) & (EA.type == attrtype)).get()
        except DoesNotExist:
            pass
        else:
            with database.atomic():
                ea.delete_instance()

    @staticmethod
    def get_attribute_list():
        return AttributeType.get_attribute_list()

    def add_interface(self, name, ifindex=None, interface_type=None,
                      macaddr=None, ipaddr=None, network=None):
        if interface_type is not None and isinstance(interface_type, str):
            interface_type = InterfaceType.select().where(InterfaceType.name==interface_type).get()
        if network is not None and isinstance(network, str):
            network = Networks.select().where(Networks.name==network).get()
        with database.atomic():
            Interfaces.create(name=name, equipment=self, ifindex=ifindex,
                interface_type=interface_type, macaddr=macaddr, ipaddr=ipaddr,
                network=network)

    def attach_interface(self, **selectkw):
        """Attach an existing interface entry that is currently detached."""
        q = Interfaces.select()
        for attrname, value in selectkw.items():
            q = q.where(getattr(Interfaces, attrname) == value)
        intf = q.get()
        if intf.equipment is not None:
            raise ModelError("Interface already attached to {!r}".format(intf.equipment))
        with database.atomic():
            intf.equipment = self

    def del_interface(self, name):
        with database.atomic():
            intf = self.interfaces.where(Interfaces.name == name).get()
            intf.delete_instance()

    def connect(self, intf, network, force=False):
        """Connect this equipments named interface to a network.

        If "force" is True then alter network part of address to match
        network.
        """
        intf = self.interfaces.where(Interfaces.name == intf).get()
        if isinstance(network, str):
            network = Networks.select().where(Networks.name==network).get()
        # alter the IP mask to match the network
        addr = intf.ipaddr
        if addr is not None and network.ipnetwork is not None:
            addr.maskbits = network.ipnetwork.maskbits
            if addr.network != network.ipnetwork.network:
                if force:
                    addr.network = network.ipnetwork.network
                else:
                    raise ModelError("Can't add interface to network with different network numbers.")
            intf.ipaddr = addr
        intf.network = network
        session.commit()

    def disconnect(self, session, intf):
        intf = self.interfaces[intf]
        intf.network = None
        session.commit()



class ClientSession(BaseModel):
    """Persist browser-based application context."""
    data = PickleField()
    expire_date = DateTimeTZField()
    session_key = CharField(max_length=40, primary_key=True, unique=True)

    class Meta:
        db_table = 'client_session'


class Components(BaseModel):
    name = CharField(max_length=255, unique=True)
    description = TextField(null=True)
    created = DateTimeTZField(default=time_now)

    class Meta:
        db_table = 'components'


class ProjectCategory(BaseModel):
    name = CharField(max_length=80, unique=True)

    class Meta:
        db_table = 'project_category'


class Projects(BaseModel):
    name = CharField(max_length=255, unique=True)
    description = TextField(null=True)
    created = DateTimeTZField(default=time_now)
    category = ForeignKeyField(db_column='category_id', null=True,
                               rel_model=ProjectCategory, to_field='id',
                               related_name="projects",
                               on_update="CASCADE", on_delete="SET NULL")
    leader = ForeignKeyField(db_column='leader_id', null=True,
                             rel_model=Contacts, to_field='id',
                             related_name="projects")

    class Meta:
        db_table = 'projects'


class TestSuites(BaseModel):
    name = CharField(max_length=255, unique=True)
    purpose = TextField(null=True)
    lastchange = DateTimeTZField(default=time_now)
    lastchangeauthor = ForeignKeyField(db_column='lastchangeauthor_id',
                                       null=True,
                                       rel_model=User, to_field='id',
                                       related_name="testsuites",
                                       on_update="CASCADE",
                                       on_delete="SET NULL")
    project = ForeignKeyField(db_column='project_id', null=True,
                              rel_model=Projects, to_field='id',
                              related_name="testsuites",
                              on_update="CASCADE", on_delete="SET NULL")
    suiteimplementation = CharField(max_length=255, null=True)
    valid = BooleanField()

    class Meta:
        db_table = 'test_suites'


class _ComponentsSuites(BaseModel):
    component = ForeignKeyField(db_column='component_id',
                                rel_model=Components, to_field='id',
                                related_name="suites")
    testsuite = ForeignKeyField(db_column='testsuite_id',
                                rel_model=TestSuites, to_field='id',
                                related_name="components")

    class Meta:
        db_table = 'components_suites'
        primary_key = CompositeKey('component', 'testsuite')


class RequirementRef(BaseModel):
    ROW_DISPLAY = ("uri",)
    uri = CharField(max_length=255)
    description = TextField(null=True)

    class Meta:
        db_table = 'requirement_ref'

    def __str__(self):
        return "Requirement: {}".format(self.uri)


class TestCases(BaseModel):
    ROW_DISPLAY = ("name", "purpose", "testimplementation")

    name = CharField(max_length=255, unique=True)
    purpose = TextField(null=True)
    passcriteria = TextField(null=True)
    startcondition = TextField(null=True)
    endcondition = TextField(null=True)
    procedure = TextField(null=True)
    comments = TextField(null=True)
    automated = BooleanField()
    testimplementation = CharField(max_length=255, null=True)
    type = EnumField(constants.TestCaseType,
                     default=constants.TestCaseType.Unknown)
    priority = EnumField(constants.Priority,
                         default=constants.Priority.Unknown)
    status = EnumField(constants.Status,
                       default=constants.Status.Unknown)
    interactive = BooleanField(default=False)
    lastchange = DateTimeTZField(default=time_now)
    bugid = CharField(max_length=80, null=True)
    time_estimate = IntervalField(null=True)
    valid = BooleanField()
    author = ForeignKeyField(db_column='author_id', null=True,
                             rel_model=User, to_field='id',
                             related_name="testcases_author",
                             on_update="CASCADE", on_delete="SET NULL")
    lastchangeauthor = ForeignKeyField(db_column='lastchangeauthor_id',
                                       null=True,
                                       rel_model=User, to_field='id',
                                       related_name="testcase_changes",
                                       on_update="CASCADE",
                                       on_delete="SET NULL")
    reference = ForeignKeyField(db_column='reference_id', null=True,
                                rel_model=RequirementRef, to_field='id',
                                related_name="testcases",
                                on_update="CASCADE", on_delete="SET NULL")
    reviewer = ForeignKeyField(db_column='reviewer_id', null=True,
                               rel_model=User, to_field='id',
                               related_name="testcase_reviews",
                               on_update="CASCADE", on_delete="SET NULL")
    tester = ForeignKeyField(db_column='tester_id', null=True,
                             rel_model=User, to_field='id',
                             related_name="testcases_tester",
                             on_update="CASCADE", on_delete="SET NULL")

    class Meta:
        db_table = 'test_cases'
        indexes = (
            (("testimplementation",), False),
            )

    def __str__(self):
        return self.name


class Config(BaseModel):
    ROW_DISPLAY = ("name", "value", "user")
    name = CharField(max_length=80)
    parent = ForeignKeyField(db_column='parent_id', null=True,
                             rel_model='self', to_field='id')
    value = PickleField(null=True)
    testcase = ForeignKeyField(db_column='testcase_id', null=True,
                               rel_model=TestCases, to_field='id',
                               related_name="config")
    user = ForeignKeyField(db_column='user_id', null=True,
                           rel_model=User, to_field='id',
                           related_name="config",
                           on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'config'
        indexes = (
            (("name", "parent"), True),
            )

    def __str__(self):
        if self.value is NULL:
            return "<{!s}>".format(self.name)
        else:
            return "{!s}={!r}".format(self.name, self.value)

    def __repr__(self):
        return "Config(name={!r}, value={!r})".format(self.name, self.value)

    def set_owner(self, user):
        q = Config.update(user=user).where(Config.id == self.id)
        q.execute()

    def get_child(self, name):
        q = Config.select().filter(
            (Config.parent == self) & (Config.name == name))
        try:
            return q.get()
        except DoesNotExist:
            raise ModelError("No sub-node {!r} set.".format(name))

    @property
    def children(self):
        return Config.select().where(Config.parent == self).execute()


class CorpAttributeType(BaseModel):
    name = CharField(max_length=80, unique=True)
    description = TextField(null=True)
    value_type = EnumField(constants.ValueType)

    class Meta:
        db_table = 'corp_attribute_type'


class _CorpAttributes(BaseModel):
    corporation = ForeignKeyField(db_column='corporation_id',
                                  rel_model=Corporations, to_field='id',
                                  related_name="attributes")
    type = ForeignKeyField(db_column='type_id',
                           rel_model=CorpAttributeType, to_field='id')
    value = PickleField()

    class Meta:
        db_table = 'corp_attributes'
        primary_key = CompositeKey('corporation', 'type')


class FunctionalArea(BaseModel):
    name = CharField(max_length=255, unique=True)
    description = CharField(max_length=255, null=True)

    class Meta:
        db_table = 'functional_area'

    def __str__(self):
        return "FunctionalArea: {}".format(self.name)


class Function(BaseModel):
    name = CharField(max_length=80, unique=True)
    description = TextField(null=True)

    class Meta:
        db_table = 'function'

    def __str__(self):
        return "Function: {}".format(self.name)

    @classmethod
    def get_by_name(cls, name):
        try:
            attrtype = cls.select().where(cls.name == str(name)).get()
        except DoesNotExist:
            raise ModelError("No Function {!r} defined.".format(name))
        return attrtype

class EnvironmentAttributeType(BaseModel):
    name = CharField(max_length=80, unique=True)
    description = TextField(null=True)
    value_type = EnumField(constants.ValueType)

    class Meta:
        db_table = 'environmentattribute_type'

    @classmethod
    def get_attribute_list(cls):
        return cls.select(cls.name, cls.value_type).tuples()


class Environments(BaseModel):
    ROW_DISPLAY = ("name", "owner")
    name = CharField(max_length=255, unique=True)
    owner = ForeignKeyField(db_column='owner_id', null=True,
                            rel_model=User, to_field='id',
                            related_name="environments",
                            on_update="CASCADE", on_delete="SET NULL")

    class Meta:
        db_table = 'environments'

    def __str__(self):
        return self.name

    def update_attribute(self, attrname, value):
        attrtype = EnvironmentAttributeType.get_by_name(attrname)
        EA = _EnvironmentAttributes
        try:
            existing = EA.select().where(
                (EA.equipment == self) & (EA.type == attrtype)).get()
        except DoesNotExist:
            self.set_attribute(attrname, value)
        else:
            with database.atomic():
                existing.value = coerce_value_type(attrtype.value_type, value)

    def set_attribute(self, attrname, value):
        attrtype = EnvironmentAttributeType.get_by_name(attrname)
        value = coerce_value_type(attrtype.value_type, value)
        with database.atomic():
            _EnvironmentAttributes(equipment=self, type=attrtype, value=value)

    def get_attribute(self, attrname):
        attrtype = EnvironmentAttributeType.get_by_name(attrname)
        EA = _EnvironmentAttributes
        try:
            ea = EA.select().where(
                (EA.equipment == self) & (EA.type == attrtype)).get()
        except DoesNotExist:
            raise ModelAttributeError(
                "No attribute {!r} set.".format(attrname))
        return ea.value

    def del_attribute(self, attrname):
        attrtype = EnvironmentAttributeType.get_by_name(attrname)
        EA = _EnvironmentAttributes
        try:
            ea = EA.select().where(
                (EA.equipment == self) & (EA.type == attrtype)).get()
        except DoesNotExist:
            pass
        else:
            with database.atomic():
                ea.delete_instance()

    @staticmethod
    def get_attribute_list():
        return EnvironmentAttributeType.get_attribute_list()

    def get_supported_roles(self):
        roles = set()
        for te in Testequipment.select().where(
                Testequipment.environment == self):
            for role in te.roles:
                roles.add(role.function.name)
        return roles

    def get_DUT(self):
        qq = Testequipment.select().where(
            (Testequipment.environment == self) & (Testequipment.DUT == True))  # noqa
        eq = qq.first()
        if eq is None:
            raise ModelError(
                "DUT is not defined in environment '{}'.".format(self.name))
        return eq.equipment

    def add_testequipment(self, eq, rolename):
        if rolename == "DUT":
            with database.atomic():
                te = Testequipment.create(
                    DUT=True, environment=self, equipment=eq)
        else:
            func = Function.select().where(Function.name == rolename).get()
            with database.atomic():
                te = Testequipment.create(
                    DUT=False, environment=self, equipment=eq)
                _TestequipmentRoles.create(testequipment=te, function=func)

    def get_equipment_with_role(self, rolename):
        TE = Testequipment # shorthand
        role = Function.get_by_name(rolename)
        qq = TE.select().where(
            TE.environment == self & TE.DUT == False & TE.roles == role)
        try:
            te = qq.get()
        except DoesNotExist:
            raise ModelError("No role '{}' defined in environment '{}'.".format(
                rolename, self.name))
        return te.equipment

    def get_all_equipment_with_role(self, rolename):
        pass


class Testequipment(BaseModel):
    DUT = BooleanField(db_column='DUT')
    environment = ForeignKeyField(db_column='environment_id',
                                  rel_model=Environments, to_field='id',
                                  related_name="testequipment",
                                  on_update="CASCADE", on_delete="CASCADE")
    equipment = ForeignKeyField(db_column='equipment_id',
                                rel_model=Equipment, to_field='id',
                                related_name="testequipment",
                                on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'testequipment'
        indexes = (
            (("environment", "equipment"), True),
            )


class _TestequipmentRoles(BaseModel):
    testequipment = ForeignKeyField(db_column='testequipment_id',
                                    rel_model=Testequipment, to_field='id',
                                    related_name="roles")
    function = ForeignKeyField(db_column='function_id',
                               rel_model=Function, to_field='id')

    class Meta:
        db_table = 'testequipment_roles'
        primary_key = CompositeKey('testequipment', 'function')


class _EnvironmentAttributes(BaseModel):
    environment = ForeignKeyField(db_column='environment_id',
                                  rel_model=Environments, to_field='id',
                                  related_name="attributes")
    type = ForeignKeyField(db_column='type_id',
                           rel_model=EnvironmentAttributeType, to_field='id')
    value = PickleField()

    class Meta:
        db_table = 'environment_attributes'
        primary_key = CompositeKey('environment', 'type')


class _EquipmentAttributes(BaseModel):
    equipment = ForeignKeyField(db_column='equipment_id',
                                rel_model=Equipment, to_field='id',
                                related_name="attributes")
    type = ForeignKeyField(db_column='type_id',
                           rel_model=AttributeType, to_field='id')
    value = PickleField()

    class Meta:
        db_table = 'equipment_attributes'
        primary_key = CompositeKey('equipment', 'type')


class _EquipmentModelAttributes(BaseModel):
    equipmentmodel = ForeignKeyField(db_column='equipmentmodel_id',
                                     rel_model=EquipmentModel, to_field='id',
                                     related_name="attributes")
    type = ForeignKeyField(db_column='type_id',
                           rel_model=AttributeType, to_field='id')
    value = PickleField()

    class Meta:
        db_table = 'equipment_model_attributes'
        primary_key = CompositeKey('equipmentmodel', 'type')


class Software(BaseModel):
    name = CharField(max_length=255, unique=True)
    implements = ForeignKeyField(db_column='category_id',
                                 rel_model=Function, to_field='id',
                                 related_name="implementations")
    manufacturer = ForeignKeyField(db_column='manufacturer_id', null=True,
                                   rel_model=Corporations, to_field='id',
                                   related_name="softwares")
    vendor = ForeignKeyField(db_column='vendor_id', null=True,
                             rel_model=Corporations, to_field='id',
                             related_name="vended_software")

    class Meta:
        db_table = 'software'


class _EquipmentModelEmbeddedsoftware(BaseModel):
    equipmentmodel = ForeignKeyField(db_column='equipmentmodel_id',
                                     rel_model=EquipmentModel, to_field='id',
                                     related_name="embedded_software")
    software = ForeignKeyField(db_column='software_id',
                               rel_model=Software, to_field='id')

    class Meta:
        db_table = 'equipment_model_embeddedsoftware'
        primary_key = CompositeKey('equipmentmodel', 'software')


class _EquipmentSoftware(BaseModel):
    equipment = ForeignKeyField(db_column='equipment_id',
                                rel_model=Equipment, to_field='id',
                                related_name="software")
    software = ForeignKeyField(db_column='software_id',
                               rel_model=Software, to_field='id',
                               related_name="hardware")

    class Meta:
        db_table = 'equipment_software'
        primary_key = CompositeKey('equipment', 'software')


class _EquipmentSubcomponents(BaseModel):
    from_equipment = ForeignKeyField(db_column='from_equipment_id',
                                     rel_model=Equipment, to_field='id',
                                     related_name="partof")
    to_equipment = ForeignKeyField(db_column='to_equipment_id',
                                   rel_model=Equipment, to_field='id',
                                   related_name="components")

    class Meta:
        db_table = 'equipment_subcomponents'
        primary_key = CompositeKey('from_equipment', 'to_equipment')


class InterfaceType(BaseModel):
    name = CharField(max_length=40)
    enumeration = IntegerField(null=True)

    class Meta:
        db_table = 'interface_type'

    def __str__(self):
        return "{}({})".format(self.name, self.enumeration)


class Networks(BaseModel):
    ROW_DISPLAY = ("name", "layer", "vlanid", "ipnetwork", "notes")
    name = CharField(max_length=64)
    ipnetwork = CIDRField(null=True)  # cidr
    layer = IntegerField()
    lower = ForeignKeyField(db_column='lower_id', null=True,
                            rel_model='self', to_field='id')
    notes = TextField(null=True)
    vlanid = IntegerField(null=True)

    class Meta:
        db_table = 'networks'

    def __str__(self):
        if self.layer == 2 and self.vlanid is not None:
            return "{} <{}>".format(self.name, self.vlanid)
        elif self.layer == 3 and self.ipnetwork is not None:
            return "{} ({})".format(self.name, self.ipnetwork)
        else:
            return "{}[{}]".format(self.name, self.layer)


class Interfaces(BaseModel):
    ROW_DISPLAY = ("name", "ifindex", "interface_type", "equipment",
                   "macaddr", "ipaddr", "network")
    name = CharField(max_length=64)
    alias = CharField(max_length=64, null=True)
    ifindex = IntegerField(null=True)
    description = TextField(null=True)
    speed = IntegerField(null=True)
    status = IntegerField(null=True)
    ipaddr = IPv4Field(null=True)  # inet
    macaddr = MACField(null=True)  # macaddr
    vlan = IntegerField(null=True)
    mtu = IntegerField(null=True)
    parent = ForeignKeyField(db_column='parent_id', null=True,
                             rel_model='self', to_field='id')
    equipment = ForeignKeyField(db_column='equipment_id', null=True,
                                rel_model=Equipment, to_field='id',
                                related_name="interfaces")
    interface_type = ForeignKeyField(db_column='interface_type_id', null=True,
                                     rel_model=InterfaceType, to_field='id')
    network = ForeignKeyField(db_column='network_id', null=True,
                              rel_model=Networks, to_field='id')

    class Meta:
        db_table = 'interfaces'

    def __str__(self):
        return "{} ({})".format(self.name, self.ipaddr)


class LanguageSets(BaseModel):
    name = CharField(max_length=80, unique=True)

    class Meta:
        db_table = 'language_sets'


class _LanguageSetsLanguages(BaseModel):
    language = ForeignKeyField(db_column='language_id',
                               rel_model=LanguageCodes, to_field='id',
                               related_name="sets")
    languageset = ForeignKeyField(db_column='languageset_id',
                                  rel_model=LanguageSets, to_field='id')

    class Meta:
        db_table = 'language_sets_languages'
        primary_key = CompositeKey('language', 'languageset')


class ProjectVersions(BaseModel):
    project = ForeignKeyField(db_column='project_id',
                              rel_model=Projects, to_field='id',
                              related_name="versions")
    major = IntegerField(default=1)
    minor = IntegerField(default=0)
    subminor = IntegerField(default=0)
    build = IntegerField(null=True)
    valid = BooleanField()

    class Meta:
        db_table = 'project_versions'
        indexes = (
            (("project", "major", "minor", "subminor", "build"), True),
            )

    def __str__(self):
        return "{} {}.{}.{}-{}".format(self.project, self.major, self.minor,
                                       self.subminor, self.build)


class _ProjectsComponents(BaseModel):
    component = ForeignKeyField(db_column='component_id',
                                rel_model=Components, to_field='id',
                                related_name="projects")
    project = ForeignKeyField(db_column='project_id',
                              rel_model=Projects, to_field='id',
                              related_name="components")

    class Meta:
        db_table = 'projects_components'
        primary_key = CompositeKey('component', 'project')


class RiskCategory(BaseModel):
    name = CharField(max_length=80, unique=True)
    description = TextField(null=True)

    class Meta:
        db_table = 'risk_category'

    def __str__(self):
        return self.name


class RiskFactors(BaseModel):
    description = TextField(null=True)
    likelihood = EnumField(constants.Likelihood)
    severity = EnumField(constants.Severity)
    priority = EnumField(constants.Priority)
    requirement = ForeignKeyField(db_column='requirement_id', null=True,
                                  rel_model=RequirementRef, to_field='id',
                                  related_name="risk_factors")
    risk_category = ForeignKeyField(db_column='risk_category_id', null=True,
                                    rel_model=RiskCategory, to_field='id',
                                    related_name="factors")
    testcase = ForeignKeyField(db_column='testcase_id', null=True,
                               rel_model=TestCases, to_field='id',
                               related_name="risk_factors")

    class Meta:
        db_table = 'risk_factors'


class Schedule(BaseModel):
    """Cron style time schedule."""
    name = CharField(max_length=80)
    hour = CharField(max_length=80)
    minute = CharField(max_length=80)
    month = CharField(max_length=80)
    day_of_month = CharField(max_length=80)
    day_of_week = CharField(max_length=80)
    user = ForeignKeyField(db_column='user_id', null=True,
                           rel_model=User, to_field='id',
                           related_name="schedules",
                           on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'schedule'
        indexes = (
            (("name", "user"), True),
            )

    def __str__(self):
        return self.name


class _SoftwareAttributes(BaseModel):
    software = ForeignKeyField(db_column='software_id',
                               rel_model=Software, to_field='id')
    type = ForeignKeyField(db_column='type_id',
                           rel_model=AttributeType, to_field='id')
    value = PickleField()

    class Meta:
        db_table = 'software_attributes'
        primary_key = CompositeKey('software', 'type')


class SoftwareVariant(BaseModel):
    name = CharField(max_length=80, unique=True)
    country = ForeignKeyField(db_column='country_id', null=True,
                              rel_model=CountryCodes, to_field='id')
    encoding = CharField(max_length=80, null=True)
    language = ForeignKeyField(db_column='language_id', null=True,
                               rel_model=LanguageCodes, to_field='id',
                               related_name="softwares")

    class Meta:
        db_table = 'software_variant'


class _SoftwareVariants(BaseModel):
    software = ForeignKeyField(db_column='software_id',
                               rel_model=Software, to_field='id',
                               related_name="variants")
    softwarevariant = ForeignKeyField(db_column='softwarevariant_id',
                                      rel_model=SoftwareVariant, to_field='id')

    class Meta:
        db_table = 'software_variants'
        primary_key = CompositeKey('software', 'softwarevariant')


class _TestCasesAreas(BaseModel):
    testcase = ForeignKeyField(db_column='testcase_id',
                               rel_model=TestCases, to_field='id',
                               related_name="test_areas")
    functionalarea = ForeignKeyField(db_column='functionalarea_id',
                                     rel_model=FunctionalArea, to_field='id')

    class Meta:
        db_table = 'test_cases_areas'
        primary_key = CompositeKey('testcase', 'functionalarea')


class _TestCasesPrerequisites(BaseModel):
    testcase = ForeignKeyField(db_column='testcase_id',
                               rel_model=TestCases, to_field='id',
                               related_name="secondary")
    prerequisite = ForeignKeyField(db_column='prerequisite_id',
                                   rel_model=TestCases, to_field='id',
                                   related_name="prerequisites")

    class Meta:
        db_table = 'test_cases_prerequisites'
        primary_key = CompositeKey('testcase', 'prerequisite')


class TestJobs(BaseModel):
    ROW_DISPLAY = ("name",)
    name = CharField(max_length=80)
    environment = ForeignKeyField(db_column='environment_id',
                                  rel_model=Environments, to_field='id')
    isscheduled = BooleanField()
    parameters = TextField(null=True)
    reportname = CharField(max_length=80)
    schedule = ForeignKeyField(db_column='schedule_id', null=True,
                               rel_model=Schedule, to_field='id')
    testsuite = ForeignKeyField(db_column='testsuite_id',
                                rel_model=TestSuites, to_field='id',
                                related_name="jobs")
    user = ForeignKeyField(db_column='user_id',
                           rel_model=User, to_field='id',
                           related_name="testjobs",
                           on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'test_jobs'
        indexes = (
            (("name", "user"), True),
            )

    def __str__(self):
        return self.name


class UseCases(BaseModel):
    ROW_DISPLAY = ("name",)
    name = CharField(max_length=255, unique=True)
    purpose = TextField(null=True)
    notes = TextField(null=True)

    class Meta:
        db_table = 'use_cases'

    def __str__(self):
        return self.name


class TestResults(BaseModel):
    testimplementation = CharField(max_length=255, null=True)
    objecttype = EnumField(constants.ObjectTypes)
    result = EnumField(constants.TestResult)
    testversion = CharField(max_length=255, null=True)
    arguments = CharField(max_length=255, null=True)
    diagnostic = TextField(null=True)
    starttime = DateTimeTZField(null=True)
    endtime = DateTimeTZField(null=True)
    note = TextField(null=True)
    reportfilename = CharField(max_length=255, null=True)
    valid = BooleanField(default=True)
    environment = ForeignKeyField(db_column='environment_id', null=True,
                                  rel_model=Environments, to_field='id')
    parent = ForeignKeyField(db_column='parent_id', null=True,
                             rel_model='self', to_field='id')
    build = ForeignKeyField(db_column='build_id', null=True,
                            rel_model=ProjectVersions, to_field='id')
    resultslocation = CharField(max_length=255, null=True)
    testcase = ForeignKeyField(db_column='testcase_id', null=True,
                               rel_model=TestCases, to_field='id',
                               related_name="results")
    tester = ForeignKeyField(db_column='tester_id', null=True,
                             rel_model=User, to_field='id',
                             related_name="testresults",
                             on_update="CASCADE", on_delete="SET NULL")
    testsuite = ForeignKeyField(db_column='testsuite_id', null=True,
                                rel_model=TestSuites, to_field='id',
                                related_name="results")

    class Meta:
        db_table = 'test_results'


class TestResultsData(BaseModel):
    data = JSONField()
    note = CharField(max_length=255, null=True)
    test_results = ForeignKeyField(db_column='test_results_id',
                                   rel_model=TestResults, to_field='id',
                                   related_name="data",
                                   on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'test_results_data'


class _TestSuitesSuites(BaseModel):
    from_testsuite = ForeignKeyField(db_column='from_testsuite_id',
                                     rel_model=TestSuites, to_field='id',
                                     related_name="suites_from")
    to_testsuite = ForeignKeyField(db_column='to_testsuite_id',
                                   rel_model=TestSuites, to_field='id',
                                   related_name="suites_to")

    class Meta:
        db_table = 'test_suites_suites'
        primary_key = CompositeKey('from_testsuite', 'to_testsuite')


class _TestSuitesTestcases(BaseModel):
    testcase = ForeignKeyField(db_column='testcase_id',
                               rel_model=TestCases, to_field='id',
                               related_name="testsuites")
    testsuite = ForeignKeyField(db_column='testsuite_id',
                                rel_model=TestSuites, to_field='id',
                                related_name="subsuites")

    class Meta:
        db_table = 'test_suites_testcases'
        primary_key = CompositeKey('testcase', 'testsuite')


# Attribute type coercion to specified type.
def coerce_value_type(value_type, value):
    try:
        return _COERCE_MAP[value_type](value)
    except (ValueError, TypeError) as err:
        raise ModelValidationError(err)


def _coerce_float(value):
    return float(value)


def _coerce_int(value):
    return int(value)


def _coerce_boolean(value):
    if isinstance(value, str):
        value = value.lower()
        if value in ("on", "1", "true", "t", "y", "yes"):
            return True
        elif value in ("off", "0", "false", "f", "n", "no"):
            return False
        else:
            raise ModelValidationError(
                "Invalid boolean string: {!r}".format(value))
    else:
        return bool(value)


def _coerce_object(value):
    if isinstance(value, str):
        try:
            return eval(value, {}, {})
        except:
            ex, val, tb = sys.exc_info()
            del tb
            raise ModelValidationError(
                "Could not evaluate object: {}: {}".format(ex, __name__, val))
    else:
        return value


def _coerce_string(value):
    return str(value)


_COERCE_MAP = {
    constants.ValueType.Object: _coerce_object,
    constants.ValueType.String: _coerce_string,
    constants.ValueType.Integer: _coerce_int,
    constants.ValueType.Float: _coerce_float,
    constants.ValueType.Boolean: _coerce_boolean,
}


# Introspection for metadata
def get_columns(class_):
    """Returns a list of ColumnMetadata.
    """
    return database.get_columns(class_._meta.db_table)


def get_foreign_keys(class_):
    return database.get_foreign_keys(class_._meta.db_table)


def get_metadata(class_):
    return get_columns(class_) + get_foreign_keys(class_)


def get_column_metadata(class_, colname):
    for colmd in get_columns(class_):
        if colmd.name == colname:
            return colmd


def get_rowdisplay(class_):
    return getattr(class_, "ROW_DISPLAY", None) or [t.name for t in
                                                    get_columns(class_)]


def get_primary_key_name(table):
    """Return name or names of primary key column. Return None if not defined.
    """
    pk = database.get_primary_keys(table._meta.db_table)
    pk_l = len(pk)
    if pk_l == 0:
        return None
    elif pk_l == 1:
        return pk[0]
    else:
        return tuple(pk)


def get_primary_key_value(dbrow):
    pkname = get_primary_key_name(dbrow.__class__)
    if pkname:
        return getattr(dbrow, str(pkname))
    else:
        raise ModelError("No primary key for this row: {!r}".format(dbrow))


def get_tables():
    return tuple(TABLES)


_DBSCHEMES = {
    'postgres': PostgresqlDatabase,
    'postgresql': PostgresqlDatabase,
    'sqlite': SqliteDatabase,
}


def connect(url=None):
    global database, database_proxy
    if database is not None:
        return
    if not url:
        cf = basicconfig.get_config("database3.conf")
        url = cf["DATABASE_URL"]
    url = urlparse.urlparse(url)
    dbclass = _DBSCHEMES.get(url.scheme)
    if dbclass is None:
        raise ValueError("Unsupported database: {}".format(url.scheme))
    kwargs = {"autocommit": False}
    if url.scheme.startswith("postgres"):
        kwargs['database'] = url.path[1:]
        if url.username:
            kwargs['user'] = url.username
        if url.password:
            kwargs['password'] = url.password
        if url.hostname:
            kwargs['host'] = url.hostname
    else:
        kwargs['database'] = url.path
    # Create db and initialize proxy to new db
    database = dbclass(**kwargs)
    database_proxy.initialize(database)


_ASSOC_TABLES = [
    "_AuthGroupPermissions", "_AuthUserUserPermissions", "_AuthUserGroups",
    "_ComponentsSuites", "_CorpAttributes", "_EnvironmentAttributes",
    "_EquipmentAttributes", "_EquipmentModelAttributes",
    "_EquipmentModelEmbeddedsoftware", "_EquipmentSoftware",
    "_EquipmentSubcomponents", "_LanguageSetsLanguages", "_ProjectsComponents",
    "_SoftwareAttributes", "_SoftwareVariants", "_TestCasesAreas",
    "_TestCasesPrerequisites", "_TestSuitesSuites", "_TestSuitesTestcases",
    "_TestequipmentRoles", ]
