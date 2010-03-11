# -*- coding: utf-8 -*-
"""Sets of items, with the ability to do additions and substractions. 
RangeSet are very efficient in storage, as they store ranges, e.g. [6,8-15,24-32,48]

This module is a wrapper around the datatype module, and is offered as seamless 
replacement of the rangeset module.
"""

# WRAPPER AROUND DATATYPE RANGE OBJECTS.

import re
import math
# local module
import datatype

class Range(datatype.Range):
    """Abstract range class. Ranges represent a finite part within a 1-dimensional (e.g. ordered) item space.
    A range has a minimum and a maximum. For example [4-5], "a-f" or <5.3...6.8].
    This class is abstract, and is a superclass for the actual classes ContinuousRange and DiscreteRange."""
    def __init__(self, min=None, max=None, itemtype=None, interval=None, mininclusive=True, maxinclusive=True):
        raise NotImplementedError("Range is an abstract class. You must instantiate a subclass (e.g. ContinuousRange or DiscreteRange)")

class ContinuousRange(datatype.ContinuousRange):
    """Continuous finite range with lower and upper limit. E.g. [3-5] or [3,5> (if 5 is not included). 
    The items must be countable. E.g. integers, floats, chars."""
    def __new__(cls, min=None, max=None, mininclusive=True, maxinclusive=True, itemtype=None):
        if itemtype in [float]:
            type = datatype.FloatType()
            if mininclusive and maxinclusive:
                return type.getRange(min, max, minmodifier=0, maxmodifier=0)
            elif not mininclusive:
                return type.getRange(min, max, minmodifier=+1, maxmodifier=0)
            else:
                return type.getRange(min, max, minmodifier=0, maxmodifier=-1)
        elif itemtype in [str, unicode]:
            type = StringType()
            if mininclusive and maxinclusive:
                return type.getRange(min, max, minmodifier=0, maxmodifier=0)
            elif not mininclusive:
                return type.getRange(min, max, minmodifier=+1, maxmodifier=0)
            else:
                return type.getRange(min, max, minmodifier=0, maxmodifier=-1)
        else: # if itemtype in [int, long]:
            type = datatype.IntegerType()
            if not mininclusive:
                min += 1
            if not maxinclusive:
                max -= 1
            return type.getRange(min, max)
    
    def __init__(self, min=None, max=None, mininclusive=True, maxinclusive=True, itemtype=None):
        pass

class DiscreteRange(datatype.CountableRange):
    """Finite arithmic progression with lower and upper limit. Since a progression is discrete, 
    it is always inclusive the first and last items. The items must be countable. E.g. integers, floats, or longs."""
    def __init__(self, min=None, max=None, itemtype=int, interval=1):
        if itemtype == int:
            type = datatype.IntegerType() #interval?
        elif itemtype == float:
            type = datatype.DiscreteFloat(interval)
        else:
            raise TypeError("Item %s has type %s. Only countable (i.e. numerical) types are supported." % (str(itemtype), type(itemtype).__name__))
        datatype.CountableRange.__init__(self, min, max, type)
    

class RangeSet(datatype.RangeSet):
    """A set of ordered items, stored in ranges. E.g. [6,8-15,24-32,48] 
    instead of [6,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,32,48]"""
    """The parts that make up the rangeset."""
    def __init__(self, string_or_array=None, interval=None, itemtype=None):
        pass

class ContinuousRangeSet(datatype.ContinuousRangeSet):
    def __init__(self, string_or_array=None, interval=None, itemtype=None):
        pass


class DiscreteRangeSet(datatype.CountableRangeSet):
    def __init__(self, string_or_array=None, interval=None, itemtype=None):
        pass


