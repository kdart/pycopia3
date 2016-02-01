#!/usr/bin/env python3.5
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Main stock admin interface.
"""

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView
from flask.ext.basicauth import BasicAuth

from pycopia.QA.db import models

app = Flask(__name__)
app.secret_key = 'sKlS(32@hpYbdlKD94$$kldspcwldkKDAld'

app.config['BASIC_AUTH_USERNAME'] = 'admin'
app.config['BASIC_AUTH_PASSWORD'] = 'pycopia'
app.config['SESSION_TYPE'] = 'filesystem'

# @basic_auth.required

@app.before_request
def _db_connect():
    models.database.connect()


@app.teardown_request
def _db_close(exc):
    if not models.database.is_closed():
        models.database.close()


admin = Admin(app, name='Admin', template_mode='bootstrap3')

admin.add_view(ModelView(models.User))

app.run(debug=True, use_reloader=False)
