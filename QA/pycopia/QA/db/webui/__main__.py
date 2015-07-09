#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

"""
WebUI main application. Used only for testing. Usually these apps are run from
the web server framework (pycopia.WWW).
"""

from pycopia.QA.db import models
from pycopia.QA.db.webui import app


@app.before_request
def _db_connect():
    models.database.connect()


@app.teardown_request
def _db_close(exc):
    if not models.database.is_closed():
        models.database.close()


app.run(debug=True, use_reloader=False)
