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
WebUI views.
"""

from pycopia.QA.db import models
from pycopia.QA.db import config

from pycopia.QA.db.webui import app

from flask import (url_for, Blueprint, abort, redirect, request, session, g,
                   render_template, render_template_string, make_response,
                   escape, json, jsonify)
from flask.ext.restful import (reqparse, Api, Resource, fields, marshal_with)


@app.route("/")
def index():
    cssurl = url_for('static', filename='style.css')
    menuitems = [
        "Run Tests",
        "Manage Config",
        "Manage Environments",
        "Manage Lab Equipment",
        "Test Run Reports",
        ]
    return render_template("index.html", mainstyle=cssurl, items=menuitems)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        request.form["username"]
        request.form["password"]
        request.form["key"]
        redir = request.form["redir"]
        # TODO do_the_login()
        return jsonify(redir=redir, code=200)
        # return jsonify(error="Invalid login", code=401)
    else:
        return render_template("login.html", message="Testing", key="testkey",
                               redirect="/")


@app.route("/db")
def db():
    return render_template("db.html", mainstyle=cssurl)


# RESTful API

class ConfigList(Resource):

    def get(self):
        cf = config.get_config()
        return list(cf.keys())

    def post(self):
        args = argparser.parse_args()
        # return str(args)
        return ["TODO post", args]


class Config(Resource):

    def get(self, key):
        args = argparser.parse_args()
        cf = config.get_config()
        value = cf.get(key)
        if isinstance(value, config.Container):
            value = dict(value)
        return ["TODO get", key, cf.get(key)]

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


class Equipment(Resource):

    def get(self, eqid):
        EQ = models.Equipment
        return EQ.select().where(EQ.id == eqid).get()

    def put(self, key):
        pass

    def delete(self, key):
        pass


api = Api(app)
api.add_resource(ConfigList, '/api1/config')
api.add_resource(Config, '/api1/config/<string:key>')
api.add_resource(EquipmentList, '/api1/equipment')
api.add_resource(Equipment, '/api1/equipment/<int:eqid>')


