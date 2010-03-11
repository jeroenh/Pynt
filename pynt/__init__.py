# -*- coding: utf-8 -*-
"""Exceptions used in the network hierarchy"""

# built-in modules
import sys
import string

# Check python version
if sys.version_info[:3] < (2, 4, 0):
    raise ImportError("The installed version of python, %s, is too old. 2.4 or higher is required" % string.split(sys.version)[0])
    # otherwise, we get SyntaxErrors for @staticmethods, etc.

version = "0.1" # for point releases
# release = int("$Revision$"[11:-2])  # for subversion revisions
# releasedate = "$Date$"[7:32] # extract the date, time, timezone only


class ConsistencyException(Exception):
    "Raised when the addition of an object leads to an internal inconsistency, not handled by the model"
    pass

