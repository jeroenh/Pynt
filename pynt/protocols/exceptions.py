# -*- coding: utf-8 -*-
"""Exceptions used by the protocols package"""


class NetworkException(IOError):
    "Raised when a network device can not be reached"
    pass

class CommandFailed(Exception):
    "Raised when a command resulted in an error from the remote peer"
    pass

class TimeOut(Exception):
    "Raised when the remote peer times out"
    pass

class MalformedIO(Exception):
    "Raised when an input or output strings is malformed"
    pass

