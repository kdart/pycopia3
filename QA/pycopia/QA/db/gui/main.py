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

"""


import kivy
kivy.require("1.9.0")

from kivy.app import App
# from kivy.properties import ObjectProperty
from kivy.uix.button import Button
# from kivy.uix.floatlayout import FloatLayout
# from kivy.uix.popup import Popup

from pycopia.QA.db import config


class ConfigEditorApp(App):

#    def on_start(self):
#        pass

    def on_quit(self):
        pass

    def do_hello(self):
        print("Hello")


def main(argv):
    app = ConfigEditorApp()
    app.run()


if __name__ == "__main__":
    import sys
    main(sys.argv)

