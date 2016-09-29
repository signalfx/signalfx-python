### CHANGELOG

This file documents important changes to the SignalFx Python client library.

- [[1.0.6] - 2016-09-29: More Python 3 compatibility](#106---2016-09-29-more-python-3-compatibility)
- [[1.0.5] - 2016-09-29: Python 3 compatibility](#105---2016-09-29-python-3-compatibility)
- [[1.0.1] - 2016-06-02: Support for SignalFlow API](#101---2016-06-02-support-for-signalflow-api)

#### [1.0.6] - 2016-09-29: More Python 3 compatibility

Version 1.0.6 includes an updated version of the generated
ProtocolBuffer code, generated with version 3 of the Protocol Buffer
compiler and library, which produces Python 3 compatible Python source
code.

#### [1.0.5] - 2016-09-29: Python 3 compatibility

Version 1.0.5 of the SignalFx Python client library provides compatibility for
Python 3.x.

#### [1.0.1] - 2016-06-02: Support for SignalFlow API

In version 1.0.1 of this client, we introduced support for the SignalFlow API.
This means you can use this client to programmatically stream analytical
computations from SignalFx in real time, in addition to sending data in to
SignalFx. Using SignalFlow, you can build your own applications that leverage
SignalFx's streaming analytics outside the SignalFx UI. To read more about
SignalFlow, click here: https://developers.signalfx.com/docs/signalflow-overview

Adding support for SignalFlow required upgrades to this client that are
backwards-incompatible with previous versions. Customers who are upgrading from
version 0.3.9 or earlier must change how the client is instantiated in
application code, and how it is authorized.

##### 1. Client instantiation

Each client's features are now divided among data transmission to SignalFx
(`ingest`), metadata retrieval (`rest`), and data streaming from SignalFx to
your client (`signalflow`).  This means that when you instantiate a SignalFx
client object, you must also choose which SignalFx API you will access using
that object.

- If you use the client to send data to SignalFx, use `ingest`.
- If you use the client to retrieve metric names and metadata from SignalFx,
  use `rest`.
- To use the new SignalFlow API to stream analytics to your client,
  use `signalflow`.

Before SignalFlow support, client instantiation used to look like this:

```python
import signalfx

sfx = signalfx.SignalFx('ACCESS_TOKEN')
```

After SignalFlow support, client instantiation now looks like this:

```python
import signalfx

sfx = signalfx.SignalFx()

# To send data from client to SignalFx using the ingest API
ingest = sfx.ingest('API_SESSION_TOKEN')

# To get and set properties and tags using the REST API
rest = sfx.rest('USER_SESSION_TOKEN')

# To stream data from SignalFx to client using the SignalFlow API
flow = sfx.signalflow('USER_SESSION_TOKEN')
```


##### 2. Authenticating to SignalFx

As illustrated in the above example, instead of supplying an access token at the
moment of instantiating a SignalFx client object, you must now supply it when
you choose which API to access.

- For `ingest`, supply your API session token. Obtain this token from within the
  SignalFx app.
- For `rest` and `signalflow`, first authenticate with your SignalFx credentials,
  then supply your user session token. [Click here to read about SignalFx authentication](https://developers.signalfx.com/docs/authentication-overview).

You can authenticate using cURL as in the following example:

```python
curl -s -XPOST -HContent-Type:application/json https://api.signalfx.com/v2/session -d'{"email":"USERNAME","password":"PASSWORD"}' | jq -r '.accessToken'
```

Alternatively, you could authenticate to SignalFx programmatically from within
this client:

```python
import signalfx
sfx = signalfx.SignalFx()
token = sfx.login("USERNAME", "PASSWORD")
```
