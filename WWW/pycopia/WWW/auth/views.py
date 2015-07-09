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
