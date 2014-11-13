"""Collection of runtime reports.

"""

import locale

from pycopia.QA.exceptions import ReportFindError


def get_report(config):
    from . import default
    # TODO selection based on config
    if locale.getpreferredencoding() == 'UTF-8':
        return default.DefaultReportUnicode()
    else:
        return default.DefaultReport()

