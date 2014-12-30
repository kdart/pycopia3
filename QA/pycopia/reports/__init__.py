"""Collection of runtime reports.

"""

import locale

from pycopia.QA.exceptions import ReportFindError


def get_report(config):
    from . import default
    rname = config.get("reportname", "default")
    if rname.startswith("default"):
        if locale.getpreferredencoding() == 'UTF-8':
            return default.DefaultReportUnicode()
        else:
            return default.DefaultReport()
    else:
        raise ReportFindError("No report {} defined.".format(rname))

