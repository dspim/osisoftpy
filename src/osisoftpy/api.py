# -*- coding: utf-8 -*-

#    Copyright 2017 DST Controls
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
"""
osisoftpy.api
~~~~~~~~~~~~
This module implements the OSIsoftPy API.
"""

import logging

from osisoftpy.factory import Factory, create
from osisoftpy.internal import get
from osisoftpy.webapi import WebAPI

log = logging.getLogger(__name__)


def webapi(
        url,
        authtype='kerberos',
        username=None,
        password=None,
        verifyssl=False):

    r = get(url, authtype=authtype, username=username, password=password, verifyssl=verifyssl)
    return create(Factory(WebAPI), r.response.json(), r.session)


def request(url, **kwargs):
    r = get(url, **kwargs)
    return r.response


def setloglevel(loglevel):
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel.upper())
    log.setLevel(loglevel.upper())
    print('Log level: %s' % log.level)

