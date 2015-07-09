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
WebUI views. Implements an Angular application. Angular fragments are also
served from here.
"""

import ast

from pycopia.QA.db import models
from pycopia.QA.db import config

from pycopia.QA.db.webui import app

from flask import (url_for, make_response, abort, redirect, request, session, g)

from flask.ext.restful import (reqparse, Api, Resource, fields, marshal_with)



ANGULAR_FRAGMENTS = {
        "testme": "<testme></testme>",
}

@app.route("/fragments/<string:name>")
def fragments(name):
    frag = ANGULAR_FRAGMENTS.get(name)
    if frag:
        return frag
    else:
        abort(404)


# RESTful API

class ConfigList(Resource):

    def get(self):
        cf = config.get_config()
        return list(cf.keys())


class Config(Resource):

    def get(self, key):
        args = argparser.parse_args()
        cf = config.get_config()
        value = cf.get(key)
        if isinstance(value, config.Container):
            value = dict(value)
        return ["TODO get", key, cf.get(key)]

    def post(self, key):
        args = argparser.parse_args()
        cf = config.get_config()
        value = ast.literal_eval(args["value"])
        cf[key] = value

    def put(self, key):
        args = argparser.parse_args()
        return ["TODO put", key, args]

    def delete(self, key):
        args = argparser.parse_args()
        return ["TODO delete", key, args]


class EquipmentList(Resource):

    def get(self):
        EQ = models.Equipment
        return list(EQ.select(EQ.id, EQ.name).tuples())

    def post(self):
        pass

class TableList(Resource):

    def get(self):
        return models.get_tables()


class Equipment(Resource):

    def get(self, eqid):
        EQ = models.Equipment
        return EQ.select().where(EQ.id == eqid).get()

    def put(self, key):
        pass

    def delete(self, key):
        pass


api = Api(app)
api.add_resource(TableList, '/')
api.add_resource(ConfigList, '/keys')
api.add_resource(Config, '/keys/<string:key>')
api.add_resource(EquipmentList, '/equipment')
api.add_resource(Equipment, '/equipment/<int:eqid>')

