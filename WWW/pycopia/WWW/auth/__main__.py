"""
Run as package for testing only.
"""

from pycopia.WWW.auth import app

app.run(debug=True, use_reloader=True)
