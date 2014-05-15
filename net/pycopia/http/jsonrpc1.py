#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2012- Keith Dart <keith@dartworks.biz>
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
JSON RPC v1.0 over HTTP.
"""

import json

from pycopia import urls
from pycopia.inet import httputils
from pycopia.http.client import (HTTPRequest, RequestResponseError)


class JSONError(Exception):
    pass

class JSONRequestError(JSONError):
    pass

class JSONResponseError(JSONError):
    pass


def Counter():
    i = 0
    while True:
        yield i
        i += 1


class JSON1Method:
    COUNTER = Counter() # class singleton

    def __init__(self, name, params):
        self.method = name
        self.params = params
        self.id = next(self.COUNTER)

    def to_json(self):
        return json.dumps({"method": self.method, "params": self.params, "id": self.id})


class SimpleJSONRPCClient:

    def __init__(self, url, logfile=None):
        self._baseurl = urls.UniversalResourceLocator(url)
        self._cookiejar = httputils.CookieJar()
        self._logfile = logfile

    def call(self, path, query, method, args):
        """Call the remote method, return result.
        """
        data = JSON1Method(method, args)
        resp = self.post(path, data, query)
        res = json.loads(resp.body.decode("utf-8"))
        if res["id"] != data.id:
            raise JSONRequestError("mismatched id")
        err = res.get("error")
        if err:
            raise JSONResponseError((err["code"], err["message"]))
        return res["result"]

    def get(self, path, query=None):
        url = self._baseurl.copy()
        url.path = self._baseurl.path + path
        headers = [httputils.Referer(self._baseurl), httputils.Connection("keep-alive")]
        request = HTTPRequest(url, method="GET", query=query, cookiejar=self._cookiejar, extraheaders=headers)
        resp = request.perform(self._logfile)
        if resp.status.code != 200:
            raise RequestResponseError(str(resp.status))
        self._cookiejar.parse_mozilla_lines(resp.cookielist)
        return resp

    def post(self, path, data, query=None):
        url = self._baseurl.copy()
        url.path = self._baseurl.path + path
        if query:
            url.query = query
        request = HTTPRequest(url, data, method="POST", cookiejar=self._cookiejar,
                accept="application/json")
        resp = request.perform(self._logfile)
        if resp.status.code != 200:
            raise RequestResponseError(str(resp.status))
        self._cookiejar.parse_mozilla_lines(resp.cookielist)
        return resp

    @property
    def cookies(self):
        return self._cookiejar.get_setcookies()

    def clear_cookies(self):
        return self._cookiejar.clear()



if __name__ == "__main__":
    m = JSON1Method("callme", ("maybe", 1))
    print(m.to_json())
    m = JSON1Method("callme", ("again", 2))
    print(m.to_json())

