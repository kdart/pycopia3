"""
Applet for authentication.
"""

# This import pattern is what Flask requires.

from flask import Flask

app = Flask(__name__)

from . import views
