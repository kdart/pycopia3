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
Data model for QA framework. May also serve a base for lab management, since it contains complete
information about all equipment and networks.
"""

# Every table a QA framework could ever want. ;)
TABLES = ['AccountIds', 'CountryCodes', 'Addresses', 'AttributeType', 'User', 'UserMessage',
    'AuthGroup', 'AuthPermission', 'Contacts', 'Corporations', 'EquipmentCategory',
    'EquipmentModel', 'Location', 'LanguageCodes', 'Equipment', 'CapabilityGroup', 'CapabilityType',
    'ClientSession', 'Components', 'ProjectCategory', 'Projects', 'TestSuites', 'RequirementRef',
    'TestCases', 'Config', 'CorpAttributeType', 'FunctionalArea', 'CorporationsServices',
    'EnvironmentattributeType', 'Environments', 'Function', 'Software', 'InterfaceType', 'Networks',
    'Interfaces', 'LanguageSets', 'ProjectVersions', 'RiskCategory', 'RiskFactors', 'Schedule',
    'SoftwareVariant', 'TestJobs', 'TestResults', 'TestResultsData', 'Testequipment', 'UseCases']

__all__ = TABLES + ["get_rowdisplay"]

import os
import collections
from datetime import datetime
from hashlib import sha1
from urllib import parse as urlparse

from pytz import timezone
from peewee import *

from pycopia import basicconfig
from pycopia.aid import hexdigest, unhexdigest, NULL
from pycopia.QA.exceptions import ModelError
from pycopia.QA.db.fields import *


# default value constructors

UTC = timezone('UTC')

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


class CountryCodes(BaseModel):
    isocode = CharField(max_length=4)
    name = CharField(max_length=80)

    class Meta:
        db_table = 'country_codes'

class Addresses(BaseModel):
    address = TextField()
    address2 = TextField(null=True)
    city = CharField(max_length=80, null=True)
    country = ForeignKeyField(db_column='country_id', null=True,
            rel_model=CountryCodes, to_field='id')
    postalcode = CharField(max_length=15, null=True)
    stateprov = CharField(max_length=80, null=True)

    class Meta:
        db_table = 'addresses'

class AttributeType(BaseModel):
    description = TextField(null=True)
    name = CharField(max_length=80)
    value_type = IntegerField()

    class Meta:
        db_table = 'attribute_type'


class User(BaseModel):
    ROW_DISPLAY = ("username", "first_name", "last_name", "email")
    first_name = CharField(max_length=30)
    middle_name = CharField(max_length=30, null=True)
    last_name = CharField(max_length=30)
    address = ForeignKeyField(db_column='address_id', null=True, rel_model=Addresses, to_field='id')
    username = CharField(max_length=30)
    _password = CharField(db_column="password", max_length=40, null=True)
    authservice = CharField(max_length=20)
    last_login = DateTimeField(default=time_now)
    date_joined = DateTimeField()
    email = CharField(max_length=75, null=True)
    is_active = BooleanField()
    is_staff = BooleanField()
    is_superuser = BooleanField()

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

    # Passwords are stored in the database encrypted.
    @property
    def password(self):
        from Crypto.Cipher import AES
        eng = AES.new(_get_key(), AES.MODE_ECB)
        return eng.decrypt(unhexdigest(self._password)).strip(b"\0").decode("utf8")

    @password.setter
    def password(self, passwd):
        # Using pycrypto package.
        from Crypto.Cipher import AES
        eng = AES.new(_get_key(), AES.MODE_ECB)
        passwd = passwd[:16].encode("utf-8")
        self._password = hexdigest(eng.encrypt((passwd + b"\0"*(16 - len(passwd)))[:16]))

    def get_session_key(self):
        h = sha1()
        h.update(str(self.id))
        h.update(self.username)
        h.update(str(self.last_login))
        return h.hexdigest()

    @classmethod
    def get_by_username(cls, username):
        return cls.select().filter(cls.username==username).first()


_SECRET_KEY = None
def _get_secret():
    global _SECRET_KEY
    try:
        cf = basicconfig.get_config("auth.conf")
    except basicconfig.ConfigReadError:
        print("User encryption key not found for auth app, using default.", file=sys.stderr)
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
            related_name="messages", on_update="CASCADE", on_delete="CASCADE")
    message = TextField()

    class Meta:
        db_table = 'user_message'


#### permissions
class AuthGroup(BaseModel):
    name = CharField(max_length=80)
    description = TextField()

    class Meta:
        db_table = 'auth_group'

class AuthPermission(BaseModel):
    name = CharField(max_length=50)
    description = TextField()

    class Meta:
        db_table = 'auth_permission'

class _AuthGroupPermissions(BaseModel):
    group = ForeignKeyField(db_column='group_id', rel_model=AuthGroup, to_field='id')
    permission = ForeignKeyField(db_column='permission_id', rel_model=AuthPermission, to_field='id',
            related_name="groups")

    class Meta:
        db_table = 'auth_group_permissions'

class _AuthUserUserPermissions(BaseModel):
    permission = ForeignKeyField(db_column='permission_id', rel_model=AuthPermission, to_field='id',
            related_name="users")
    user = ForeignKeyField(db_column='user_id', rel_model=User, to_field='id',
            related_name="permissions", on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'auth_user_user_permissions'

class _AuthUserGroups(BaseModel):
    group = ForeignKeyField(db_column='group_id', rel_model=AuthGroup, to_field='id')
    user = ForeignKeyField(db_column='user_id', rel_model=User, to_field='id',
            related_name="groups", on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'auth_user_groups'
####

class Contacts(BaseModel):
    address = ForeignKeyField(db_column='address_id', null=True, rel_model=Addresses, to_field='id')
    email = CharField(max_length=80, null=True)
    fax = CharField(max_length=25, null=True)
    firstname = CharField(max_length=50)
    lastname = CharField(max_length=50)
    middlename = CharField(max_length=50, null=True)
    note = TextField(null=True)
    pager = CharField(max_length=25, null=True)
    phonehome = CharField(max_length=25, null=True)
    phonemobile = CharField(max_length=25, null=True)
    phoneoffice = CharField(max_length=25, null=True)
    phoneother = CharField(max_length=25, null=True)
    phonework = CharField(max_length=25, null=True)
    position = CharField(max_length=100, null=True)
    prefix = CharField(max_length=15, null=True)
    title = CharField(max_length=50, null=True)
    user = ForeignKeyField(db_column='user_id', null=True, rel_model=User, to_field='id',
            related_name="contacts", on_update="CASCADE", on_delete="SET NULL")
    class Meta:
        db_table = 'contacts'

class Corporations(BaseModel):
    address = ForeignKeyField(db_column='address_id', null=True, rel_model=Addresses, to_field='id')
    contact = ForeignKeyField(db_column='contact_id', null=True, rel_model=Contacts, to_field='id',
            related_name="corporations")
    country = ForeignKeyField(db_column='country_id', null=True, rel_model=CountryCodes, to_field='id')
    name = CharField(max_length=255)
    notes = TextField(null=True)
    parent = ForeignKeyField(db_column='parent_id', null=True, rel_model='self', to_field='id')

    class Meta:
        db_table = 'corporations'

class EquipmentCategory(BaseModel):
    name = CharField(max_length=80)

    class Meta:
        db_table = 'equipment_category'

class EquipmentModel(BaseModel):
    category = ForeignKeyField(db_column='category_id', rel_model=EquipmentCategory, to_field='id',
            related_name="categories")
    manufacturer = ForeignKeyField(db_column='manufacturer_id', rel_model=Corporations, to_field='id',
            related_name="manufacturers")
    name = CharField(max_length=255)
    note = TextField(null=True)
    picture = CharField(max_length=255, null=True)
    specs = CharField(max_length=255, null=True)

    class Meta:
        db_table = 'equipment_model'

class Location(BaseModel):
    address = ForeignKeyField(db_column='address_id', null=True, rel_model=Addresses, to_field='id')
    contact = ForeignKeyField(db_column='contact_id', null=True, rel_model=Contacts, to_field='id',
            related_name="locations", on_update="CASCADE", on_delete="SET NULL")
    locationcode = CharField(max_length=80)

    class Meta:
        db_table = 'location'

class LanguageCodes(BaseModel):
    isocode = CharField(max_length=6)
    name = CharField(max_length=80)

    class Meta:
        db_table = 'language_codes'

class Equipment(BaseModel):
    account = ForeignKeyField(db_column='account_id', null=True, rel_model=AccountIds, to_field='id')
    active = BooleanField()
    addeddate = DateTimeField(null=True)
    comments = TextField(null=True)
    language = ForeignKeyField(db_column='language_id', null=True,
            rel_model=LanguageCodes, to_field='id', related_name="equipment")
    location = ForeignKeyField(db_column='location_id', null=True, rel_model=Location, to_field='id',
            related_name="equipment")
    model = ForeignKeyField(db_column='model_id', rel_model=EquipmentModel, to_field='id',
            related_name="equipment")
    name = CharField(max_length=255)
    owner = ForeignKeyField(db_column='owner_id', null=True, rel_model=User, to_field='id',
            related_name="equipment", on_update="CASCADE", on_delete="SET NULL")
    parent = ForeignKeyField(db_column='parent_id', null=True, rel_model='self', to_field='id')
    serno = CharField(max_length=255, null=True)
    sublocation = TextField(null=True)
    vendor = ForeignKeyField(db_column='vendor_id', null=True, rel_model=Corporations, to_field='id',
            related_name="vended")

    class Meta:
        db_table = 'equipment'

class CapabilityGroup(BaseModel):
    name = CharField(max_length=80)

    class Meta:
        db_table = 'capability_group'

class CapabilityType(BaseModel):
    description = TextField(null=True)
    group = ForeignKeyField(db_column='group_id', null=True, rel_model=CapabilityGroup, to_field='id',
            related_name="capability_types", on_update="CASCADE", on_delete="CASCADE")
    name = CharField(max_length=80)
    value_type = IntegerField()

    class Meta:
        db_table = 'capability_type'

class _Capability(BaseModel):
    equipment = ForeignKeyField(db_column='equipment_id',
            rel_model=Equipment, to_field='id', related_name="capabilities")
    type = ForeignKeyField(db_column='type_id', rel_model=CapabilityType, to_field='id',
            related_name="capabilities")
    value = TextField()

    class Meta:
        db_table = 'capability'

class ClientSession(BaseModel):
    data = TextField()
    expire_date = DateTimeField()
    session_key = CharField(max_length=40, primary_key=True)

    class Meta:
        db_table = 'client_session'

class Components(BaseModel):
    created = DateTimeField()
    description = TextField()
    name = CharField(max_length=255)

    class Meta:
        db_table = 'components'

class ProjectCategory(BaseModel):
    name = CharField(max_length=80)

    class Meta:
        db_table = 'project_category'

class Projects(BaseModel):
    category = ForeignKeyField(db_column='category_id', null=True,
            rel_model=ProjectCategory, to_field='id', related_name="projects",
                    on_update="CASCADE", on_delete="SET NULL")
    created = DateTimeField()
    description = TextField()
    leader = ForeignKeyField(db_column='leader_id', null=True, rel_model=Contacts, to_field='id',
            related_name="projects")
    name = CharField(max_length=255)

    class Meta:
        db_table = 'projects'

class TestSuites(BaseModel):
    lastchange = DateTimeField()
    lastchangeauthor = ForeignKeyField(db_column='lastchangeauthor_id', null=True,
            rel_model=User, to_field='id', related_name="testsuites",
            on_update="CASCADE", on_delete="SET NULL",
            )
    name = CharField(max_length=255)
    project = ForeignKeyField(db_column='project_id', null=True,
            rel_model=Projects, to_field='id', related_name="testsuites",
            on_update="CASCADE", on_delete="SET NULL")
    purpose = TextField(null=True)
    suiteimplementation = CharField(max_length=255, null=True)
    valid = BooleanField()

    class Meta:
        db_table = 'test_suites'

class _ComponentsSuites(BaseModel):
    component = ForeignKeyField(db_column='component_id', rel_model=Components, to_field='id',
            related_name="suites")
    testsuite = ForeignKeyField(db_column='testsuite_id', rel_model=TestSuites, to_field='id',
            related_name="components")

    class Meta:
        db_table = 'components_suites'

class RequirementRef(BaseModel):
    description = TextField(null=True)
    uri = CharField(max_length=255, null=True)

    class Meta:
        db_table = 'requirement_ref'

class TestCases(BaseModel):
    author = ForeignKeyField(db_column='author_id', null=True, rel_model=User, to_field='id',
            related_name="testcases_author", on_update="CASCADE", on_delete="SET NULL")
    automated = BooleanField()
    bugid = CharField(max_length=80, null=True)
    comments = TextField(null=True)
    cycle = IntegerField()
    endcondition = TextField(null=True)
    interactive = BooleanField()
    lastchange = DateTimeField(default=time_now)
    lastchangeauthor = ForeignKeyField(db_column='lastchangeauthor_id', null=True,
            rel_model=User, to_field='id', related_name="testcase_changes",
            on_update="CASCADE", on_delete="SET NULL")
    name = CharField(max_length=255)
    passcriteria = TextField(null=True)
    priority = IntegerField()
    procedure = TextField(null=True)
    purpose = TextField(null=True)
    reference = ForeignKeyField(db_column='reference_id', null=True,
            rel_model=RequirementRef, to_field='id', related_name="testcases",
            on_update="CASCADE", on_delete="SET NULL")
    reviewer = ForeignKeyField(db_column='reviewer_id', null=True, rel_model=User, to_field='id',
            related_name="testcase_reviews",
            on_update="CASCADE", on_delete="SET NULL")
    startcondition = TextField(null=True)
    status = IntegerField()
    tester = ForeignKeyField(db_column='tester_id', null=True, rel_model=User, to_field='id',
            related_name="testcases_tester",
            on_update="CASCADE", on_delete="SET NULL")
    testimplementation = CharField(max_length=255, null=True)
    #time_estimate = IntervalField(null=True)  # interval
    valid = BooleanField()

    class Meta:
        db_table = 'test_cases'

class Config(BaseModel):
    ROW_DISPLAY = ("name", "value", "user")
    comment = TextField(null=True)
    name = CharField(max_length=80)
    parent = ForeignKeyField(db_column='parent_id', null=True, rel_model='self', to_field='id')
    testcase = ForeignKeyField(db_column='testcase_id', null=True,
            rel_model=TestCases, to_field='id', related_name="config")
    user = ForeignKeyField(db_column='user_id', null=True, rel_model=User, to_field='id',
            related_name="config", on_update="CASCADE", on_delete="CASCADE")
    value = PickleField(null=True)

    class Meta:
        db_table = 'config'

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
        q = Config.select().filter((Config.parent==self) & (Config.name==name))
        try:
            return q.get()
        except DoesNotExist:
            raise ModelError("No sub-node {!r} set.".format(name))

    @property
    def children(self):
        return Config.select().where(Config.parent==self).execute()


class CorpAttributeType(BaseModel):
    description = TextField(null=True)
    name = CharField(max_length=80)
    value_type = IntegerField()

    class Meta:
        db_table = 'corp_attribute_type'

class _CorpAttributes(BaseModel):
    corporation = ForeignKeyField(db_column='corporation_id', rel_model=Corporations, to_field='id',
            related_name="attributes")
    type = ForeignKeyField(db_column='type_id', rel_model=CorpAttributeType, to_field='id')
    value = TextField()

    class Meta:
        db_table = 'corp_attributes'

class FunctionalArea(BaseModel):
    description = CharField(max_length=255, null=True)
    name = CharField(max_length=255)

    class Meta:
        db_table = 'functional_area'

class CorporationsServices(BaseModel):
    corporation = ForeignKeyField(db_column='corporation_id', rel_model=Corporations, to_field='id',
            related_name="services")
    functionalarea = ForeignKeyField(db_column='functionalarea_id', rel_model=FunctionalArea, to_field='id')

    class Meta:
        db_table = 'corporations_services'

class EnvironmentattributeType(BaseModel):
    description = TextField(null=True)
    name = CharField(max_length=80)
    value_type = IntegerField()

    class Meta:
        db_table = 'environmentattribute_type'

class Environments(BaseModel):
    name = CharField(max_length=255)
    owner = ForeignKeyField(db_column='owner_id', null=True, rel_model=User, to_field='id',
            related_name="environments", on_update="CASCADE", on_delete="SET NULL")

    class Meta:
        db_table = 'environments'

class _EnvironmentAttributes(BaseModel):
    environment = ForeignKeyField(db_column='environment_id', rel_model=Environments, to_field='id')
    type = ForeignKeyField(db_column='type_id', rel_model=EnvironmentattributeType, to_field='id')
    value = TextField()

    class Meta:
        db_table = 'environment_attributes'

class _EquipmentAttributes(BaseModel):
    equipment = ForeignKeyField(db_column='equipment_id', rel_model=Equipment, to_field='id',
            related_name="attributes")
    type = ForeignKeyField(db_column='type_id', rel_model=AttributeType, to_field='id')
    value = TextField()

    class Meta:
        db_table = 'equipment_attributes'

class _EquipmentModelAttributes(BaseModel):
    equipmentmodel = ForeignKeyField(db_column='equipmentmodel_id',
            rel_model=EquipmentModel, to_field='id', related_name="attributes")
    type = ForeignKeyField(db_column='type_id', rel_model=AttributeType, to_field='id')
    value = TextField()

    class Meta:
        db_table = 'equipment_model_attributes'

class Function(BaseModel):
    description = TextField(null=True)
    name = CharField(max_length=80)

    class Meta:
        db_table = 'function'

class Software(BaseModel):
    implements = ForeignKeyField(db_column='category_id',
            rel_model=Function, to_field='id', related_name="implementations")
    manufacturer = ForeignKeyField(db_column='manufacturer_id', null=True, rel_model=Corporations, to_field='id',
            related_name="softwares")
    name = CharField(max_length=255)
    vendor = ForeignKeyField(db_column='vendor_id', null=True, rel_model=Corporations, to_field='id',
            related_name="vended_software")

    class Meta:
        db_table = 'software'

class _EquipmentModelEmbeddedsoftware(BaseModel):
    equipmentmodel = ForeignKeyField(db_column='equipmentmodel_id',
            rel_model=EquipmentModel, to_field='id', related_name="embedded_software")
    software = ForeignKeyField(db_column='software_id', rel_model=Software, to_field='id')

    class Meta:
        db_table = 'equipment_model_embeddedsoftware'

class _EquipmentSoftware(BaseModel):
    equipment = ForeignKeyField(db_column='equipment_id', rel_model=Equipment, to_field='id',
            related_name="software")
    software = ForeignKeyField(db_column='software_id', rel_model=Software, to_field='id',
            related_name="hardware")

    class Meta:
        db_table = 'equipment_software'

class _EquipmentSubcomponents(BaseModel):
    from_equipment = ForeignKeyField(db_column='from_equipment_id',
            rel_model=Equipment, to_field='id', related_name="partof")
    to_equipment = ForeignKeyField(db_column='to_equipment_id',
            rel_model=Equipment, to_field='id', related_name="components")

    class Meta:
        db_table = 'equipment_subcomponents'

class InterfaceType(BaseModel):
    enumeration = IntegerField(null=True)
    name = CharField(max_length=40)

    class Meta:
        db_table = 'interface_type'

class Networks(BaseModel):
    ipnetwork = CIDRField(null=True)  # cidr
    layer = IntegerField()
    lower = ForeignKeyField(db_column='lower_id', null=True, rel_model='self', to_field='id')
    name = CharField(max_length=64)
    notes = TextField(null=True)
    vlanid = IntegerField(null=True)

    class Meta:
        db_table = 'networks'

class Interfaces(BaseModel):
    alias = CharField(max_length=64, null=True)
    description = TextField(null=True)
    equipment = ForeignKeyField(db_column='equipment_id', null=True,
            rel_model=Equipment, to_field='id', related_name="interfaces")
    ifindex = IntegerField(null=True)
    interface_type = ForeignKeyField(db_column='interface_type_id', null=True,
            rel_model=InterfaceType, to_field='id')
    ipaddr = IPv4Field(null=True)  # inet
    macaddr = MACField(null=True)  # macaddr
    mtu = IntegerField(null=True)
    name = CharField(max_length=64)
    network = ForeignKeyField(db_column='network_id', null=True, rel_model=Networks, to_field='id')
    parent = ForeignKeyField(db_column='parent_id', null=True, rel_model='self', to_field='id')
    speed = IntegerField(null=True)
    status = IntegerField(null=True)
    vlan = IntegerField(null=True)

    class Meta:
        db_table = 'interfaces'

class LanguageSets(BaseModel):
    name = CharField(max_length=80)
    class Meta:
        db_table = 'language_sets'

class _LanguageSetsLanguages(BaseModel):
    language = ForeignKeyField(db_column='language_id', rel_model=LanguageCodes, to_field='id',
            related_name="sets")
    languageset = ForeignKeyField(db_column='languageset_id', rel_model=LanguageSets, to_field='id')

    class Meta:
        db_table = 'language_sets_languages'

class ProjectVersions(BaseModel):
    build = IntegerField(null=True)
    major = IntegerField()
    minor = IntegerField()
    project = ForeignKeyField(db_column='project_id',
            rel_model=Projects, to_field='id', related_name="versions")
    subminor = IntegerField()
    valid = BooleanField()

    class Meta:
        db_table = 'project_versions'

class _ProjectsComponents(BaseModel):
    component = ForeignKeyField(db_column='component_id', rel_model=Components, to_field='id',
            related_name="projects")
    project = ForeignKeyField(db_column='project_id', rel_model=Projects, to_field='id',
            related_name="components")

    class Meta:
        db_table = 'projects_components'

class RiskCategory(BaseModel):
    description = TextField(null=True)
    name = CharField(max_length=80)

    class Meta:
        db_table = 'risk_category'

class RiskFactors(BaseModel):
    description = TextField(null=True)
    likelihood = IntegerField()
    priority = IntegerField()
    requirement = ForeignKeyField(db_column='requirement_id', null=True,
            rel_model=RequirementRef, to_field='id', related_name="risk_factors")
    risk_category = ForeignKeyField(db_column='risk_category_id', null=True,
            rel_model=RiskCategory, to_field='id', related_name="factors")
    severity = IntegerField()
    testcase = ForeignKeyField(db_column='testcase_id', null=True,
            rel_model=TestCases, to_field='id', related_name="risk_factors")

    class Meta:
        db_table = 'risk_factors'

class Schedule(BaseModel):
    day_of_month = CharField(max_length=80)
    day_of_week = CharField(max_length=80)
    hour = CharField(max_length=80)
    minute = CharField(max_length=80)
    month = CharField(max_length=80)
    name = CharField(max_length=80)
    user = ForeignKeyField(db_column='user_id', null=True, rel_model=User, to_field='id',
            related_name="schedules", on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'schedule'

class _SoftwareAttributes(BaseModel):
    software = ForeignKeyField(db_column='software_id', rel_model=Software, to_field='id')
    type = ForeignKeyField(db_column='type_id', rel_model=AttributeType, to_field='id')
    value = TextField()

    class Meta:
        db_table = 'software_attributes'

class SoftwareVariant(BaseModel):
    country = ForeignKeyField(db_column='country_id', null=True, rel_model=CountryCodes, to_field='id')
    encoding = CharField(max_length=80, null=True)
    language = ForeignKeyField(db_column='language_id', null=True,
            rel_model=LanguageCodes, to_field='id', related_name="softwares")
    name = CharField(max_length=80)

    class Meta:
        db_table = 'software_variant'

class _SoftwareVariants(BaseModel):
    software = ForeignKeyField(db_column='software_id', rel_model=Software, to_field='id')
    softwarevariant = ForeignKeyField(db_column='softwarevariant_id', rel_model=SoftwareVariant, to_field='id')

    class Meta:
        db_table = 'software_variants'

class _TestCasesAreas(BaseModel):
    functionalarea = ForeignKeyField(db_column='functionalarea_id',
            rel_model=FunctionalArea, to_field='id')
    testcase = ForeignKeyField(db_column='testcase_id',
            rel_model=TestCases, to_field='id', related_name="test_areas")

    class Meta:
        db_table = 'test_cases_areas'

class _TestCasesPrerequisites(BaseModel):
    prerequisite = ForeignKeyField(db_column='prerequisite_id',
            rel_model=TestCases, to_field='id', related_name="prerequisites")
    testcase = ForeignKeyField(db_column='testcase_id',
            rel_model=TestCases, to_field='id', related_name="secondary")

    class Meta:
        db_table = 'test_cases_prerequisites'

class TestJobs(BaseModel):
    environment = ForeignKeyField(db_column='environment_id', rel_model=Environments, to_field='id')
    isscheduled = BooleanField()
    name = CharField(max_length=80)
    parameters = TextField(null=True)
    reportname = CharField(max_length=80)
    schedule = ForeignKeyField(db_column='schedule_id', null=True, rel_model=Schedule, to_field='id')
    testsuite = ForeignKeyField(db_column='testsuite_id',
            rel_model=TestSuites, to_field='id', related_name="jobs")
    user = ForeignKeyField(db_column='user_id', rel_model=User, to_field='id',
            related_name="testjobs", on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'test_jobs'

class TestResults(BaseModel):
    arguments = CharField(max_length=255, null=True)
    build = ForeignKeyField(db_column='build_id', null=True, rel_model=ProjectVersions, to_field='id')
    diagnostic = TextField(null=True)
    endtime = DateTimeField(null=True)
    environment = ForeignKeyField(db_column='environment_id', null=True, rel_model=Environments, to_field='id')
    note = TextField(null=True)
    objecttype = IntegerField()
    parent = ForeignKeyField(db_column='parent_id', null=True, rel_model='self', to_field='id')
    reportfilename = CharField(max_length=255, null=True)
    result = IntegerField()
    resultslocation = CharField(max_length=255, null=True)
    starttime = DateTimeField(null=True)
    testcase = ForeignKeyField(db_column='testcase_id', null=True,
            rel_model=TestCases, to_field='id', related_name="results")
    tester = ForeignKeyField(db_column='tester_id', null=True, rel_model=User, to_field='id',
            related_name="testresults", on_update="CASCADE", on_delete="SET NULL")
    testimplementation = CharField(max_length=255, null=True)
    testsuite = ForeignKeyField(db_column='testsuite_id', null=True,
            rel_model=TestSuites, to_field='id', related_name="results")
    testversion = CharField(max_length=255, null=True)
    valid = BooleanField()

    class Meta:
        db_table = 'test_results'

class TestResultsData(BaseModel):
    data = TextField()
    note = CharField(max_length=255, null=True)
    test_results = ForeignKeyField(db_column='test_results_id',
            rel_model=TestResults, to_field='id', related_name="data",
                    on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'test_results_data'

class _TestSuitesSuites(BaseModel):
    from_testsuite = ForeignKeyField(db_column='from_testsuite_id',
            rel_model=TestSuites, to_field='id', related_name="suites_from")
    to_testsuite = ForeignKeyField(db_column='to_testsuite_id',
            rel_model=TestSuites, to_field='id', related_name="suites_to")

    class Meta:
        db_table = 'test_suites_suites'

class _TestSuitesTestcases(BaseModel):
    testcase = ForeignKeyField(db_column='testcase_id',
            rel_model=TestCases, to_field='id', related_name="testsuites")
    testsuite = ForeignKeyField(db_column='testsuite_id',
            rel_model=TestSuites, to_field='id', related_name="subsuites")

    class Meta:
        db_table = 'test_suites_testcases'

class Testequipment(BaseModel):
    DUT = BooleanField(db_column='DUT')
    environment = ForeignKeyField(db_column='environment_id',
            rel_model=Environments, to_field='id', related_name="equipment",
            on_update="CASCADE", on_delete="CASCADE")
    equipment = ForeignKeyField(db_column='equipment_id',
            rel_model=Equipment, to_field='id', related_name="testequipment",
            on_update="CASCADE", on_delete="CASCADE")

    class Meta:
        db_table = 'testequipment'

class _TestequipmentRoles(BaseModel):
    function = ForeignKeyField(db_column='function_id',
            rel_model=Function, to_field='id')
    testequipment = ForeignKeyField(db_column='testequipment_id',
            rel_model=Testequipment, to_field='id')

    class Meta:
        db_table = 'testequipment_roles'

class UseCases(BaseModel):
    name = CharField(max_length=255)
    notes = TextField(null=True)
    purpose = TextField(null=True)

    class Meta:
        db_table = 'use_cases'


MetaDataTuple = collections.namedtuple("MetaDataTuple",
        "coltype, colname, default, m2m, nullable, isaset")



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
        cf = basicconfig.get_config("database.conf")
        url = cf["DATABASE_URL"]
    url = urlparse.urlparse(url)
    dbclass = _DBSCHEMES.get(url.scheme)
    if dbclass is None:
        raise ValueError("Unsupported database: {}".format(url.scheme))
    kwargs = {'database': url.path[1:], "autocommit": False}
    if url.username:
        kwargs['user'] = url.username
    if url.password:
        kwargs['password'] = url.password
    if url.hostname:
        kwargs['host'] = url.hostname
    # Create db and initialize proxy to new db
    database = dbclass(**kwargs)
    database_proxy.initialize(database)


def get_metadata_iterator(modelclass):
    for col in modelclass._meta:
        yield _get_column_metadata(col)


def _get_column_metadata(col):
    coltype = col.__class__.__name__
    m2m =  False # TODO
    isaset =  isinstance(col, ForeignKeyField)
    return MetaDataTuple(coltype, col.name, col.default, m2m, col.null, isaset)

def get_metadata(class_):
    """Returns a list of MetaDataTuple structures.
    """
    return list(get_metadata_iterator(class_))

def get_rowdisplay(class_):
    return getattr(class_, "ROW_DISPLAY", None) or [t.colname for t in get_metadata(class_)]


if __name__ == "__main__":
    import sys

    _ASSOC_TABLES = [
        "_AuthGroupPermissions", "_AuthUserUserPermissions", "_AuthUserGroups", "_Capability",
        "_ComponentsSuites", "_CorpAttributes", "_EnvironmentAttributes", "_EquipmentAttributes",
        "_EquipmentModelAttributes", "_EquipmentModelEmbeddedsoftware", "_EquipmentSoftware",
        "_EquipmentSubcomponents", "_LanguageSetsLanguages", "_ProjectsComponents",
        "_SoftwareAttributes", "_SoftwareVariants", "_TestCasesAreas",
        "_TestCasesPrerequisites", "_TestSuitesSuites", "_TestSuitesTestcases",
        "_TestequipmentRoles",
        ]
    if len(sys.argv) > 1:
        connect(sys.argv[1])
        vs = vars()
        database.create_tables([vs[name] for name in TABLES + _ASSOC_TABLES], safe=True)

