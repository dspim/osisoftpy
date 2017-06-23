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
osisoftpy.tests.test_api.py
~~~~~~~~~~~~

Tests for the `osisoftpy.webapi` module.
"""

import re

import osisoftpy
import pytest
import requests
import random

from datetime import datetime, timedelta
from dateutil import parser

from .conftest import query


def test_get_webapi_object(webapi):
    assert type(webapi) == osisoftpy.WebAPI


def test_webapi_has_session(webapi):
    print(', '.join("%s: %s" % item for item in vars(webapi).items()))
    assert type(webapi.session) == requests.Session

def test_webapi_has_links(webapi):
    print(', '.join("%s: %s" % item for item in vars(webapi).items()))
    assert type(webapi.links) == dict

def test_webapi_has_str_(webapi, url):
    assert webapi.__str__() == '<OSIsoft PI Web API [{}]>'.format(url+'/')

def test_webapi_has_self_url(webapi, url):
    assert webapi.links.get('Self') == url + '/'

def test_webapi_has_self_url_property(webapi, url):
    assert webapi.url == url+ '/'

def test_webapi_has_search_url(webapi, url):
    assert webapi.links.get('Search') == url + '/search'


def test_webapi_query_sinusoid(webapi):
    tag = 'sinusoid'
    payload = dict(query="name:{}".format(tag), count=10)
    r = webapi.request(**payload)
    assert r.status_code == requests.codes.ok
    assert r.json().get('TotalHits') > 0
    assert r.json().get('Items')[0].get('Name').lower() == 'sinusoid'
    assert bool(
        re.match(r.json().get('Items')[0].get('Name'), tag, re.IGNORECASE))

def test_webapi_points_sinusoid(webapi):
    tag = 'sinusoid'
    payload = dict(query="name:{}".format(tag), count=10)
    r = webapi.points(**payload)
    assert all(isinstance(x, osisoftpy.Point) for x in r)
    assert r.__len__() == 1

def test_webapi_subscribe_typeerror(webapi):
    points = 1
    try:
        webapi.subscribe(points, 'current')
    except Exception as err:
        assert type(err) == TypeError

@pytest.mark.parametrize('query', query())
def test_webapi_points_query(webapi, query):
    payload = dict(query=query, count=1000)
    points = webapi.points(**payload)
    assert all(isinstance(x, osisoftpy.Point) for x in points)
    msg = '{} points were retrieved with the query "{}"'
    print(msg.format(points.__len__(), query))

# Subscription tests

# a list to store modified points in:
updated_points = []
def callback(sender):
    updated_points.append(sender)

# test getvalue
@pytest.mark.skipif(True, reason='Method only used for internal testing')
@pytest.mark.parametrize('query', ['name:EdwinPythonTest*'])
@pytest.mark.parametrize('stream', ['getvalue'])
def test_subscription_getvalue(webapi, query, stream, callback=callback):
    updated_points[:] = []
    points = webapi.points(query=query)
    subscriptions = webapi.subscribe(points, stream, callback=callback)
    for point in points:
        v1 = point.getvalue("5-16-2017 07:00")
        v2 = point.getvalue("5-17-2017 07:00")
    assert len(updated_points) > 0
    subscriptions = webapi.unsubscribe(points, stream)

updated_points_current = []
def callback_current(sender):
    updated_points_current.append(sender)

# test current_value
@pytest.mark.parametrize('query', ['name:EdwinPythonTest*'])
@pytest.mark.parametrize('stream', ['current'])
def test_subscription_current(webapi, query, stream, callback=callback_current):
    #clear array from previous tests
    updated_points_current[:] = []

    points = webapi.points(query=query)
    subscriptions = webapi.subscribe(points, stream, callback=callback_current)
    for point in points:
        v1 = point.current()
        point.update_values(["*"], [random.uniform(0,100)])
        v2 = point.current()
    assert len(updated_points_current) == 2 # both points updated
    subscriptions = webapi.unsubscribe(points, stream)

updated_points_end = []
def callback_end(sender):
    updated_points_end.append(sender)

# test end_value
@pytest.mark.parametrize('query', ['name:EdwinPythonEndTest'])
@pytest.mark.parametrize('stream', ['end'])
def test_subscription_end(webapi, query, stream, callback=callback_end):
    #clear array from previous tests
    updated_points_end[:] = []

    points = webapi.points(query=query)
    subscriptions = webapi.subscribe(points, stream, callback=callback_end)
    for point in points:
        point.update_values(["*"], [random.uniform(0,100)])
        v1 = point.end()
        point.update_values(["*+1m"], [random.uniform(0,100)])
        v2 = point.end()
    assert len(updated_points_end) == 1
    subscriptions = webapi.unsubscribe(points, stream)

updated_points_interp_1 = []
def callback_interp_1(sender):
    updated_points_interp_1.append(sender)

# test interpolatedattimes - assumes no one has used this tag
@pytest.mark.parametrize('query', ['name:PythonInterpolatedAtTime'])
@pytest.mark.parametrize('times', [['2017-01-01T00:00:00Z']])
def test_subscription_interpolatedattimes_single_timestamp_notify_one(webapi, query, times, ci, pythonversion, callback=callback_interp_1):
    #clear array from previous tests
    updated_points_interp_1[:] = []

    #query points (should be 1)
    points = webapi.points(query='{}_{}{}'.format(query, ci, pythonversion))
    for point in points:
        for time in times:
            #subscriber each timestamp for this point
            webapi.subscribe(points, 'interpolatedattimes', startdatetime=time, callback=callback_interp_1)

            #setup with values here: insert a value 1 day before and after timestamp: 0 to 1000
            #datetime is parsed so days can added/subtracted
            parseddatetime = parser.parse(time)
            date1 = (parseddatetime + timedelta(days=-1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            point.update_value(date1, 0)
            date2 = (parseddatetime + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            point.update_value(date2, 1000)

            #gets initial value for subscriber
            point.interpolatedattimes([time])

            #updates after value to 500, so there should be a new interpolated value
            point.update_value(date2, 500)

            #queries new point and should trigger callback function
            point.interpolatedattimes([time])
    assert len(updated_points_interp_1) == 1
    webapi.unsubscribe(points, 'interpolatedattimes')
    
updated_points_interp_2 = []
def callback_interp_2(sender):
    updated_points_interp_2.append(sender)

# test interpolatedattimes - assumes no one has used this tag
@pytest.mark.parametrize('query', ['name:PythonInterpolatedAtTime'])
@pytest.mark.parametrize('times', [['2016-05-01T00:00:00Z','2016-06-01T00:00:00Z']])
def test_subscription_interpolatedattimes_single_timestamp_notify_two(webapi, query, times, ci, pythonversion, callback=callback_interp_2):
    #clear array from previous tests
    updated_points_interp_2[:] = []
    
    #query points (should be 1)
    points = webapi.points(query='{}_{}{}'.format(query, ci, pythonversion))
    for point in points:
        for time in times:
            #subscriber each timestamp for this point
            webapi.subscribe(points, 'interpolatedattimes', startdatetime=time, callback=callback_interp_2)

            #setup with values here: insert a value 1 day before and after timestamp: 0 to 1000
            #datetime is parsed so days can added/subtracted
            parseddatetime = parser.parse(time)
            date1 = (parseddatetime + timedelta(days=-1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            point.update_value(date1, 0)
            date2 = (parseddatetime + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            point.update_value(date2, 1000)

    #gets initial values for subscriber
    point.interpolatedattimes(times)

    #queries new value and should trigger callback function
    for point in points:
        for time in times:
            #updates after value to 500, so there should be a new interpolated value
            parseddatetime = parser.parse(time)
            date2 = (parseddatetime + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            point.update_value(date2, 500)

    point.interpolatedattimes(times)
    assert updated_points_interp_2.__len__() == 2
    webapi.unsubscribe(points, 'interpolatedattimes')

updated_points_recorded = []
def callback_recorded(sender):
    updated_points_recorded.append(sender)

# test recordedattimes - assumes no one has used this tag
@pytest.mark.parametrize('query', ['name:PythonRecordedAtTime'])
@pytest.mark.parametrize('time', ['2017-01-01T00:00:00Z','2017-01-02T00:00:00Z'])
def test_subscription_recordedattimes(webapi, query, time, ci, pythonversion, callback=callback_recorded):
    #clear array from previous test
    updated_points_recorded[:] = []

    #query points (should be 1)
    points = webapi.points(query='{}_{}{}'.format(query, ci, pythonversion))
    for point in points:
        webapi.subscribe(points, 'recordedattime', startdatetime=time, callback=callback_recorded)
        # parseddatetime = parser.parse(time)
        # date = (parseddatetime + timedelta(days=-1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        point.update_value(time, 134)
        point.recordedattime(time)
        point.update_value(time, 160)
        #should trigger callback function
        point.recordedattime(time)
    assert len(updated_points_recorded) == 1
    webapi.unsubscribe(points, 'recordedattime')
