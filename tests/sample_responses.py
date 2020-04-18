#!/usr/bin/env python

# Copyright (C) 2015-2017 SignalFx, Inc. All rights reserved.

import json
import requests

# sample GET requests
r1 = requests.models.Response()
r1._content = """{
  "creator" : "BrppnRvAcAA",
  "lastUpdatedBy" : "BrppnRvAcAA",
  "created" : 1404424799704,
  "lastUpdated" : 1446643344161,
  "customProperties" : { },
  "tags" : [ ],
  "name" : "jvm.cpu.load",
  "description" : null,
  "type" : "GAUGE"
}"""
r1.status_code = 200

r2 = requests.models.Response()
r2._content = 'Unable to find the given metric.'
r2.status_code = 404

r3 = requests.models.Response()
r3._content = """{
  "results" : [ {
    "creator" : "BrppnSQAgAA",
    "lastUpdatedBy" : "BrppnSQAgAA",
    "created" : 1454373475316,
    "lastUpdated" : 1454373475321,
    "customProperties" : { },
    "name" : "not_there_yet_3",
    "description" : ""
  }, {
    "creator" : "BrppnSQAgAA",
    "lastUpdatedBy" : "BrppnSQAgAA",
    "created" : 1454368261284,
    "lastUpdated" : 1454368261289,
    "customProperties" : { },
    "name" : "not_there_yet_2",
    "description" : ""
  }, {
    "creator" : "BrppnSQAgAA",
   "lastUpdatedBy" : "BrppnSQAgAA",
    "created" : 1454366572540,
    "lastUpdated" : 1454366572540,
    "customProperties" : { },
    "name" : "not_there_yet",
    "description" : ""
  }, {
    "creator" : "BrppnSQAgAA",
    "lastUpdatedBy" : "BrppnSQAgAA",
    "created" : 1453421427363,
    "lastUpdated" : 1453423073345,
    "customProperties" : {
      "test2" : "12345"
    },
    "name" : "ozan-test",
  "description" : "hello world"
  }, {
    "creator" : "BrpxxCFAgAA",
    "lastUpdatedBy" : "BrpxxCFAgAA",
    "created" : 1404868650680,
    "lastUpdated" : 1448531708485,
 "customProperties" : {
      "service" : "tsdb"
    },
    "name" :"tsdb",
    "description" : null
  } ],
  "count" : 38
}"""

GETS = {
    'https://api.signalfx.com/v2/metric/jvm.cpu.load': r1,
    'https://api.signalfx.com/v2/metric/jvm.cpu.loaderino': r2,
    'https://api.signalfx.com/v2/tag?query=is_it_there': r3
}

# sample PUT requests
a = requests.models.Response()
a.status_code = 200
a._content = """{
  "creator" : "BrppnSQAgAA",
  "lastUpdatedBy" : "BrppnSQAgAA",
  "created" : 1454632312454,
  "lastUpdated" : 1454632312454,
  "customProperties" : { },
  "tags" : [ ],
  "description" : "",
  "key" : "kkkkk",
  "value" : "vvvvv"
}"""

b = requests.models.Response()
b.status_code = 400
b._content = ("Can not instantiate value of type [simple type, class sf.rest.v2.model.Dimension] from String value (''); "  # noqa
              "no single-String constructor/factory method\n at [Source: org.glassfish.jersey.message.internal.ReaderInterceptorExecutor$UnCloseableInputStream@2c073d76; line: 1, column: 1]")  # noqa

PUTS = {
    ('https://api.signalfx.com/v2/dimension/kkkkk/vvvvv',
        '{"description": "", "tags": [],'
        ' "customProperties": {}, "value":'
        ' "vvvvv", "key": "kkkkk"}'): a,
    ('https://api.signalfx.com/v2/dimension/kkkkk/vvvvv',
        json.dumps('')): b
}

# sample DELETE requests
x, y = requests.models.Response(), requests.models.Response()
x._content = ''
y._content = 'Unable to find the given tag.'

DELETES = {
    'https://api.signalfx.com/v2/tag/there': x,
    'https://api.signalfx.com/v2/tag/not_there': y
}
