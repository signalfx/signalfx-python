# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import random
import string


class _Channel(object):
    """Base class for open channels that receive streaming data from a
    SignalFlow computation.

    Channel objects bridge the gap between an underlying transport and a
    higher-level Computation object by providing a transport-agnostic and
    encoding-agnostic access to the stream of messages.StreamMessage objects
    that are received for a given computation.

    Channels are iterable that return messages.StreamMessage instances.
    """

    _CHANNEL_NAME_ALPHABET = (string.ascii_lowercase +
                              string.ascii_uppercase +
                              string.digits)
    _CHANNEL_NAME_LENGTH = 8

    def __init__(self):
        nonce = ''.join(random.choice(_Channel._CHANNEL_NAME_ALPHABET)
                        for _ in range(_Channel._CHANNEL_NAME_LENGTH))
        self._name = 'channel-{0}'.format(nonce)

    @property
    def name(self):
        return self._name

    def __iter__(self):
        return self

    def __str__(self):
        return 'channel<{0}>'.format(self._name)

    def next(self):
        return self._next()

    def __next__(self):
        return self._next()
