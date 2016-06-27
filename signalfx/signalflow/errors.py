# Copyright (C) 2016 SignalFx, Inc. All rights reserved.


class SignalFlowException(Exception):
    """A generic error encountered when interacting with the SignalFx
    SignalFlow API."""

    def __init__(self, code, message=None):
        self._code = code
        self._message = message

    @property
    def code(self):
        """Returns the HTTP error code."""
        return self._code

    @property
    def message(self):
        """Returns an optional error message attached to this error."""
        return self._message

    def __str__(self):
        if self._message:
            return '{0}: {1}'.format(self._code, self._message)
        return 'Error {0}'.format(self._code)


class ComputationAborted(Exception):
    """Exception thrown if the computation is aborted during its execution."""

    def __init__(self, abort_info):
        self._state = abort_info['sf_job_abortState']
        self._reason = abort_info['sf_job_abortReason']

    @property
    def state(self):
        return self._state

    @property
    def reason(self):
        return self._reason

    def __str__(self):
        return 'Computation {0}: {1}'.format(
            self._state.lower(), self._reason)


class ComputationFailed(Exception):
    """Exception thrown when the computation failed after being started."""

    def __init__(self, errors):
        self._errors = errors

    @property
    def errors(self):
        return self._errors

    def __str__(self):
        return 'Computation failed ({0})'.format(self._errors)
