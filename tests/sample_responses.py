import requests
import json

# sample GET requests
l = requests.models.Response()
l._content = '{\n  "creator" : "BrppnRvAcAA",\n  "lastUpdatedBy" : "BrppnRvAcAA",\n  ' \
             '"created" : 1404424799704,\n  "lastUpdated" : 1446643344161,\n  "customProperties"' \
             ' : { },\n  "tags" : [ ],\n  "name" : "jvm.cpu.load",\n  "description" :' \
             ' null,\n  "type" : "GAUGE"\n}'
l.status_code = 200

m = requests.models.Response()
m._content = 'Unable to find the given metric.'
m.status_code = 404

n = requests.models.Response()
n._content = '{\n  "results" : [ {\n    "creator" : "BrppnSQAgAA",\n    "lastUpdatedBy" : ' \
             '"BrppnSQAgAA",\n    "created" : 1454373475316,\n    "lastUpdated" : 1454373475321,' \
             '\n  ' '  "customProperties" : { },\n    "name" : "not_there_yet_3",\n    ' \
             '"description" : ""\n  },' ' {\n    "creator" : "BrppnSQAgAA",\n    "lastUpdatedBy" :' \
             ' "BrppnSQAgAA",\n    "created"' ' : 1454368261284,\n    "lastUpdated" : ' \
             '1454368261289,\n    "customProperties" : { },\n ' '   "name" : "not_there_yet_2",\n ' \
             '   "description" : ""\n  }, {\n    "creator" : ' '"BrppnSQAgAA",\n   ' \
             '"lastUpdatedBy" : "BrppnSQAgAA",\n    "created" : 1454366572540,\n ' \
             '   "lastUpdated" : 1454366572540,\n    "customProperties" : { },\n    "name" : ' \
             '"not_there_yet",\n    "description" : ""\n  }, {\n    "creator" : "BrppnSQAgAA",\n ' \
             '   "lastUpdatedBy" : "BrppnSQAgAA",\n    "created" : 1453421427363,\n   ' \
             ' "lastUpdated" : 1453423073345,\n    "customProperties" : {\n      "test2" :' \
             ' "12345"\n  ' '  },\n    "name" : "ozan-test",\n  "description" : "hello world"\n ' \
             ' }, {\n  ' '  "creator" : "BrpxxCFAgAA",\n    "lastUpdatedBy" : "BrpxxCFAgAA",\n  ' \
             '  "created" : 1404868650680,\n    "lastUpdated" : 1448531708485,\n ' \
             '"customProperties" ' ': {\n      "service" : "tsdb"\n    },\n    "name" :' \
             '"tsdb",\n    "description" : null\n ' ' } ],\n  "count" : 38\n}'

GETS = {
    'https://api.signalfx.com/v2/metric/jvm.cpu.load' : l,
    'https://api.signalfx.com/v2/metric/jvm.cpu.loaderino' : m,
    'https://api.signalfx.com/v2/tag?query=is_it_there': n
}


# sample PUT requests
a = requests.models.Response()
a.status_code = 200
a._content = '{\n  "creator" : "BrppnSQAgAA",\n  "lastUpdatedBy" : "BrppnSQAgAA",\n ' \
            ' "created" : 1454632312454,\n  "lastUpdated" : 1454632312454,\n  "customProperties" ' \
            ': { },\n  "tags" : [ ],\n  "description" : "",\n  "key" : "kkkkk",\n  "value" : "vvvvv"\n}'

b = requests.models.Response()
b.status_code = 400
b._content = "Can not instantiate value of type [simple type, class sf.rest.v2.model.Dimension] " \
             "from String value (''); no single-String constructor/factory method\n at [Source: " \
             "org.glassfish.jersey.message.internal.ReaderInterceptorExecutor$UnCloseableInputStream@2c073d76;" \
             " line: 1, column: 1]"

PUTS = {
    ('https://api.signalfx.com/v2/dimension/kkkkk/vvvvv', '{"description": "", "tags": [],'
                                                          ' "customProperties": {}, "value":'
                                                          ' "vvvvv", "key": "kkkkk"}'): a,
    ('https://api.signalfx.com/v2/dimension/kkkkk/vvvvv', json.dumps('')): b
}


# sample DELETE requests
x, y = requests.models.Response(), requests.models.Response()
x._content = ''
y._content = 'Unable to find the given tag.'

DELETES = {'https://api.signalfx.com/v2/tag/there' : x,
'https://api.signalfx.com/v2/tag/not_there' : y
}
