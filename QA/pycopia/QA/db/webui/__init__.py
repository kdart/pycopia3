"""
Dynamic pages for the web UI for QA framework.
"""

# This import pattern is what Flask requires.

from pycopia import logging
from pycopia.QA.db import models

from flask import Flask


models.connect()
app = Flask(__name__)
app._logger = logging.Logger(app.logger_name)

# Needs to be last.
from . import views
