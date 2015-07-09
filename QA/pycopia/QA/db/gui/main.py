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

