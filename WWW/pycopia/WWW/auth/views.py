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
Authorization views.
"""

from flask import (url_for, abort, redirect, request,
                   render_template, make_response, escape, jsonify)

from pycopia.WWW.auth import app


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


@app.route('/logout', methods=['POST'])
def logout():
    if request.method == 'POST':
        pass  # TODO
    else:
        abort(404)
