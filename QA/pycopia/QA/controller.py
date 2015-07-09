#!/usr/bin/python
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab


"""
Abstract interfaces for object controllers.

"""

class Controller:
    def __init__(self, equipment, logfile=None):
        self._equipment = equipment
        if logfile:
            self.set_logfile(logfile)
        else:
            self._logfile = None
        self.initialize()

    def __del__(self):
        self.finalize()
        self.close()

    def writelog(self, text):
        if self._logfile is not None:
            self._logfile.write(text)

    def __str__(self):
        return "<%s: %r>" % (self.__class__.__name__, self._equipment)

    def initialize(self):
        pass

    def finalize(self):
        pass

    def close(self):
        pass


