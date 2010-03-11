# -*- coding: utf-8 -*-
"""Sets of items, with the ability to do additions and substractions. 
RangeSet are very efficient in storage, as they store ranges, e.g. [6,8-15,24-32,48]

Note: this module is still used, although a newer version is written (datatype + rangeset2)
"""

import re
import math
# local module
#import datatype

class Range(object):
    """Abstract range class. Ranges represent a finite part within a 1-dimensional (e.g. ordered) item space.
    A range has a minimum and a maximum. For example [4-5], "a-f" or <5.3...6.8].
    This class is abstract, and is a superclass for the actual classes ContinuousRange and DiscreteRange."""
    min             = None
    max             = None
    itemtype        = None
    mininclusive    = True
    maxinclusive    = True
    interval        = None
    rerange         = re.compile("^([\[\<])?(\-?[\w\.]+)(\s*[\-]\s*(\-?[\w\.]+))?([\]\>])?$")  # shared object among all instances
    # rerange matches "4-5", "<4-5]" (excluding 4), "-3--1", "1.4-4.5", "aa-bf", etc.
    def __init__(self, min=None, max=None, itemtype=None, interval=None, mininclusive=True, maxinclusive=True):
        raise NotImplementedError("Range is an abstract class. You must instantiate a subclass (e.g. ContinuousRange or DiscreteRange)")
    def _stringToRange(self, rangestring):
        """Set the range by interpreting a string. e.g. "3-8", "[3-8]", or "<3-8]" (excluding 3)."""
        # print "stringToRange(%s)" % rangestring
        match = self.rerange.match(rangestring.strip())
        if match:
            if match.group(1) == "<":
                self.mininclusive = False
            if match.group(5) == ">":
                self.maxinclusive = False
            if match.group(4):
                self.min = match.group(2)
                self.max = match.group(4)
            else:
                self.min = match.group(2)
                self.max = match.group(2)
            itemtype = self._determinetype(self.min)
            self.setitemtype(itemtype)
        else:
            raise ValueError("The string '%s' is not a valid range" % (rangestring))
        try:
            self._verify()
        except (AssertionError, AttributeError, ValueError, TypeError), msg:
            raise ValueError("The string '%s' is not a valid range: %s" % (rangestring, msg))
    def _verify(self):
        pass
    def setitemtype(self, itemtype):
        """Set itemtype. Internal function. Once itemtype is set, it can not be changed anymore."""
        if self.itemtype:
            #assert(not self.itemtype) # setitemtype() should only be called if itemtype is not yet set
            return
        if not self.ordereditemtype(itemtype):
            raise TypeError("Item %s has type %s. Only ordered (i.e. numerical and string) types are supported." % (str(itemtype), type(itemtype).__name__))
        self.itemtype = itemtype
    def _determinetype(self, item):
        """determine item type based on value of self.min, either int, long, float or string, and set self.itemtype"""
        # print "determine type of %s %s" % (type(self.min).__name__, self.min)
        # assert(not self.itemtype) # determinetype() should only be called if itemtype is not yet set
        assert(item != None) # determinetype() should only be called if min is already set
        if type(item) in [int, long, float]:
            return type(item)
        try:
            value = int(item)
            return int
        except ValueError:
            pass
        try:
            value = float(item)
            return float
        except ValueError:
            pass
        try:
            value = long(item)
            return long
        except ValueError:
            pass
        return type(item)
    @staticmethod
    def countableitemtype(itemtype):
        """Returns True is the given itemtype is countable"""
        return itemtype in [int, long, float]
    @staticmethod
    def ordereditemtype(itemtype):
        """Returns True is the given itemtype is ordered"""
        return itemtype in [int, long, float, str, unicode]
    def setRange(self, minvalue, maxvalue):
        # print "set Range: %s %s" % (repr(minvalue), repr(maxvalue))
        self.min = minvalue
        self.max = maxvalue
        self._verify()
    def _Range(self, value):
        """Type conversion of value to a (sub)class of __class__, with the same properties"""
        if isinstance(value, type(self)):
            return value
        else:
            return type(self)(value)
    def copy(self):
        return type(self)(self)
    def __copy__(self):
        return type(self)(self)
    def extend(self,value):
        value = self._Range(value)
        if value.isempty():
            return
        if self.isempty():
            self.mininclusive = value.mininclusive
            self.maxinclusive = value.maxinclusive
            self.min = value.min
            self.max = value.max
            return
        if self._cmpminmin(value) > 0:
            self.mininclusive = value.mininclusive
            self.min = value.min
        if self._cmpmaxmax(value) < 0:
            self.maxinclusive = value.maxinclusive
            self.max = value.max
        self._verify()
    def union(self, value):
        """Return a union of the given attribute and the current range. 
        The result is a RangeSet object. The current range is left intact."""
        range = self.copy()
        return RangeSet([range,value])
    def difference(self, value):
        """Remove all values of the given attribute from the current range. 
        The result is a RangeSet object. The current range is left intact."""
        # if not self.overlaps(value):
        #     return RangeSet([self])
        ranges = []
        # Remaining piece of self, smaller than value.min
        if self._cmpminmin(value) < 0:
            ranges.append(type(self)(self.min, value.min, itemtype=self.itemtype, interval=self.interval, mininclusive=self.mininclusive, maxinclusive=not value.mininclusive))
        # Remaining piece of self, higher than value.max
        if self._cmpmaxmax(value) > 0:
            ranges.append(type(self)(value.max, self.max, itemtype=self.itemtype, interval=self.interval, mininclusive=not value.maxinclusive, maxinclusive=self.maxinclusive))
        return RangeSet(ranges, itemtype=self.itemtype, interval=self.interval)
    def intersection(self, value):
        """Remove the intersection of the given attribute and the current range. 
        The result is a Range object. The current range is left intact."""
        newrange = self.copy()
        newrange.intersection_update(value)
        return newrange
    def intersection_update(self, value):
        """Set the current interval to the intersection of this and the given interval."""
        value = self._Range(value)
        if value.isempty():
            self.clear()
        if self.isempty():
            return
        if self._cmpminmin(value) < 0:
            self.mininclusive = value.mininclusive
            self.min = value.min
        if self._cmpmaxmax(value) > 0:
            self.maxinclusive = value.maxinclusive
            self.max = value.max
        self._verify()
    def isempty(self):
        return self.min == None
    def __nonzero__(self):
        """x.__nonzero() <==> bool(x)"""
        return not self.isempty()
    def clear(self):
        """Removes all elements from this rangeset"""
        self.mininclusive = True
        self.maxinclusive = True
        self.min = None
        self.max = None
    def _cmpminmin(self, value):
        """Compare self.min and value.min. Note that None < i holds for all values of i"""
        if self.min == value.min:
            if self.mininclusive == value.mininclusive:
                return 0
            elif self.mininclusive:
                return -1
            else:
                return 1
        else:
            return cmp(self.min, value.min)
    def _cmpminmax(self, value):
        """Compare self.min and value.max. Note that None < i holds for all values of i"""
        if self.min == value.max:
            if self.mininclusive and value.maxinclusive:
                return 0
            else:
                return 1
        else:
            return cmp(self.min, value.max)
    def _cmpmaxmin(self, value):
        """Compare self.max and value.min. Note that None < i holds for all values of i"""
        if self.max == value.min:
            if self.maxinclusive and value.mininclusive:
                return 0
            else:
                return -1
        else:
            return cmp(self.max, value.min)
    def _cmpmaxmax(self, value):
        """Compare self.min and value.min. Note that None < i holds for all values of i"""
        if self.max == value.max:
            if self.maxinclusive == value.maxinclusive:
                return 0
            elif self.maxinclusive:
                return 1
            else:
                return -1
        else:
            return cmp(self.max, value.max)
    def issubset(self, value):
        """Value is another range. Returns True if this range is complete covered by the given range."""
        return (self._cmpminmin(value) >= 0) and (self._cmpmaxmax(value) <= 0)
    def issuperset(self, value):
        """Value is another range. Returns True if the give range is complete covered by this range."""
        return (self._cmpminmin(value) <= 0) and (self._cmpmaxmax(value) >= 0)
    def __contains__(self, value):
        if self.isempty():
            return False
        return (value >= self.min) and (value <= self.max)
    def overlaps(self, value):
        """returns True if this datarange overlaps with datarange value"""
        return not (self.__lt__(value) or self.__gt__(value))
    def connected(self, value):
        """returns True if this datarange overlaps with or is directly in succesion with datarange value"""
        value = self._Range(value)
        if self.isempty() or value.isempty():
            return False
        if self.mininclusive or value.maxinclusive:
            lower = (self.min - self.interval <= value.max)
        else:
            lower = (self.min - self.interval < value.max)
        if self.maxinclusive or value.mininclusive:
            upper = (self.max + self.interval >= value.min)
        else:
            upper = (self.max + self.interval > value.min)
        return lower and upper
        # return ((self.min <= value.max + self.interval) and (self.max + self.interval >= value.min))
    def __gt__(self,value):
        """x.__gt__(y) <==> x>y. return True if value y is a datarange or value smaller then the datarange x."""
        # print "calling __gt__ of %s" % self.__str__()
        # Note: Range(None) is smaller then any other Range. This is consistent with None < i for all integers i
        #if self.isempty() or value.isempty():
        #    return False
        value = self._Range(value)
        if self.mininclusive:
            return self.min > value.max
        else:
            return self.min >= value.max
    def __lt__(self,value):
        """x.__lt__(y) <==> x<y. return True if value y is a datarange or value bigger then the datarange x."""
        # print "calling __lt__ of %s" % self.__str__()
        # Note: Range(None) is smaller then any other Range. This is consistent with None < i for all integers i
        #if self.isempty() or value.isempty():
        #    return False
        value = self._Range(value)
        if self.maxinclusive:
            return self.max < value.min
        else:
            return self.max <= value.min
    def __le__(self, value):
        """x.__le__(y) <==> x<=y. return True if value y is a datarange or value smaller then or overlapping the datarange x."""
        # print "calling __le__"
        return not self.__gt__(value)
    def __ge__(self, value):
        """x.__le__(y) <==> x>=y. return True if value y is a datarange or value bigger then or overlapping the datarange x."""
        # print "calling __ge__"
        return not self.__lt__(value)
    def __eq__(self, value):
        """value. x.__eq__(y) <==> x==y"""
        # print "calling __eq__"
        # Note: this may be really anything. Like None.
        try:
            return (self.min == value.min) and (self.max == value.max) and \
                (self.mininclusive == value.mininclusive) and (self.maxinclusive == value.maxinclusive) and \
                (self.itemtype == value.itemtype)
        except AttributeError:
            return False
    def __ne__(self, value):
        """x.__ne__(y) <==> x!=y"""
        # print "calling __ne__"
        return not self.__eq__(value)
    def __cmp__(self, value):
        """x.__cmp__(y) <==> cmp(x,y). Returns:
        -1 if x.max < y.max
        1  if x.max > y.max
        else if x.max == y.max:
        -1 if x.min < y.min
        1  if x.min > y.min
        else if x.min == y.min:
        cmp(x.interval, y.interval) if interval exists.
        else: return 0 
        (note that None < x for all x)"""
        # print "calling __cmp__"
        value = self._Range(value)
        comp = self._cmpmaxmax(value)
        if comp == 0:
            comp = self._cmpminmin(value)
        if comp == 0:
            comp = cmp(self.interval, value.interval)
        return comp
    def __len__(self):
        """Returns the length of a given Range. Note that a length of 0 does not mean the RangeSet is empty. The length of a ContinuousRange [6-6] is 0, but it is not empty. Use isempty() to check for an empty RangeSet."""
        # print "calling __len__"
        if self.isempty():
            return 0
        else:
            return self.max - self.min
    def __str__(self):
        if self.min == self.max:
            return "[%s]" % repr(self.min)
        elif self.mininclusive and self.maxinclusive:
            return "[%s-%s]" % (repr(self.min), repr(self.max))
        elif self.mininclusive and (not self.maxinclusive):
            return "[%s-%s>" % (repr(self.min), repr(self.max))
        elif (not self.mininclusive) and self.maxinclusive:
            return "<%s-%s]" % (repr(self.min), repr(self.max))
        else:
            return "<%s-%s>" % (self.min, self.max)
    def __repr__(self):
        append = ""
        if self.itemtype in [str, unicode]:
            append += ", itemtype=%s" % self.itemtype.__name__
        if not self.mininclusive:
            append += ", mininclusive=False"
        if not self.maxinclusive:
            append += ", maxinclusive=False"
        if self.min == self.max:
            return "%s(%s%s)" % (type(self).__name__, repr(self.min), append)
        else:
            return "%s(%s,%s%s)" % (type(self).__name__, repr(self.min), repr(self.max), append)

class ContinuousRange(Range):
    """Continuous finite range with lower and upper limit. E.g. [3-5] or [3,5> (if 5 is not included). 
    The items must be countable. E.g. integers, floats, chars."""
    mininclusive    = True
    maxinclusive    = True
    interval        = 0    # typical for ContinuousRange, can't be modified
    def __init__(self, min=None, max=None, mininclusive=True, maxinclusive=True, itemtype=None):
        # print "ContinuousRange.__init__()"
        if itemtype:
            self.setitemtype(itemtype)
        # no shallow copies; due to __copy__ implementation
        # if (type(min) == ContinuousRange) and (not itemtype):  # type conversion with same type
        #     self = min
        #     return
        if isinstance(min, Range):  # type conversion: create copy
            self.min  = min.min
            self.max  = min.max
            self.mininclusive = min.mininclusive
            self.maxinclusive = min.maxinclusive
            self.setitemtype(min.itemtype)
            self._verify()
        elif min == None:
            return
        elif max == None:
            if type(min) in [str, unicode] and self.itemtype not in [str, unicode]:
                self.mininclusive = mininclusive
                self.maxinclusive = maxinclusive
                self._stringToRange(min)
            else:
                self.setitemtype(type(min))
                self.setRange(min,min,mininclusive,maxinclusive)
        else:
            self.setitemtype(type(min))
            self.setRange(min,max,mininclusive,maxinclusive)
    def setRange(self, minvalue, maxvalue, mininclusive=True, maxinclusive=True):
        # print "set Range: %s %s" % (repr(minvalue), repr(maxvalue))
        self.min = minvalue
        self.max = maxvalue
        self.mininclusive = mininclusive
        self.maxinclusive = maxinclusive
        self._verify()
    def _verify(self):
        # print "verify ContinuousRange: %s %s" % (repr(self.min), repr(self.max))
        if not self.itemtype:
            self.setitemtype(type(self.min))
        try:
            self.min = self.itemtype(self.min)
            self.max = self.itemtype(self.max)
        except TypeError:
            raise TypeError("min and max must be of type %s. They are of types %s and %s." % (self.itemtype.__name__, type(min).__name__, type(max).__name__))
        if self._cmpminmax(self) > 0:  # self.min > self.max
            self.min = None
            self.max = None
            self.mininclusive = True
            self.maxinclusive = True
    def __contains__(self, value):
        if self.isempty():
            return False
        if ((value > self.min) and (value < self.max)):
            return True
        if (value == self.min) and self.mininclusive:
            return True
        if (value == self.max) and self.maxinclusive:
            return True
        else:
            return False


class DiscreteRange(Range):
    """Finite arithmic progression with lower and upper limit. Since a progression is discrete, 
    it is always inclusive the first and last items. The items must be countable. E.g. integers, floats, or longs."""
    interval        = 1
    itemtype        = None
    def __init__(self, min=None, max=None, itemtype=None, interval=None):
        # print "DiscreteRange.__init__()"
        if itemtype:
            self.setitemtype(itemtype)
        if interval:
            self.setinterval(interval)
        # no shallow copies; due to __copy__ implementation
        # if (type(min) == DiscreteRange) and (not itemtype) and (not interval):  # type conversion with same type
        #    self = min
        #    return
        if isinstance(min, Range):  # type conversion: create copy
            self.min  = min.min
            self.max  = min.max
            self.mininclusive = min.mininclusive
            self.maxinclusive = min.maxinclusive
            if not self.itemtype:
                self.setitemtype(min.itemtype)
            self.setinterval(min.interval)
            self._verify()
        elif min == None:
            return
        elif max == None:
            if type(min) in [str, unicode]:
                self._stringToRange(min)
            else:
                self.setitemtype(type(min))
                self.setRange(min,min,interval=interval)
        else:
            self.setitemtype(type(min))
            self.setRange(min,max,interval=interval)
    def setRange(self, minvalue, maxvalue, interval=None):
        # print "set Range: %s %s" % (repr(minvalue), repr(maxvalue))
        self.min = minvalue
        self.max = maxvalue
        if interval:
            self.setinterval(interval)
        self._verify()
    def _verify(self):
        # print "verify DiscreteRange: %s %s" % (repr(self.min), repr(self.max))
        if not self.itemtype:
            self.setitemtype(type(min))
        if type(self.interval) != self.itemtype:
            self.setinterval(self.interval)
        try:
            self.min = self.itemtype(self.min)
            self.max = self.itemtype(self.max)
        except TypeError:
            raise TypeError("min and max must be of type %s. They are of types %s and %s." % (self.itemtype.__name__, type(min).__name__, type(max).__name__))
        assert(self.interval > 0)
        if self.min and not self.mininclusive:
            self.min = self.itemtype(self.interval*(math.floor(self.min/self.interval) + 1))
            self.mininclusive = True
        if self.max and not self.maxinclusive:
            self.max = self.itemtype(self.interval*(math.ceil(self.max/self.interval) - 1))
            self.maxinclusive = True
        if (self.min % self.interval) > 0:
            self.min = self.itemtype(self.interval*(math.ceil(float(self.min)/self.interval)))
        if self.max % self.interval > 0:
            self.max = self.itemtype(self.interval*(math.floor(float(self.max)/self.interval)))
        if (self.min == None) or (self.max == None) or (self._cmpminmax(self) > 0):
            self.min = None
            self.max = None
            self.mininclusive = True
            self.maxinclusive = True
    def setitemtype(self, itemtype):
        if self.itemtype:
            #assert(not self.itemtype) # setitemtype() should only be called if itemtype is not yet set
            return
        if not self.countableitemtype(itemtype):
            raise TypeError("Item %s has type %s. Only countable (i.e. numerical) types are supported." % (str(itemtype), type(itemtype).__name__))
        # print "set itemtype to %s, interval type is %s" % (itemtype.__name__, type(self.interval).__name__)
        if (itemtype == int) and (type(self.interval) == float):
            itemtype = float
        self.itemtype = itemtype
    def setinterval(self, interval):
        if self.itemtype:
            interval = self.itemtype(interval)
        if interval <= 0:
            interval = self.itemtype(1)
        self.interval = interval
    def _Range(self, value):
        """Type conversion of value to a (sub)class of __class__, with the same properties"""
        if not isinstance(value, type(self)):
            return type(self)(value)
        elif self.interval != value.interval:
            return type(self)(value, interval=self.interval)
        else:
            return value
    def copy(self, itemtype=None, interval=None):
        return type(self)(self, itemtype=itemtype, interval=interval)
    def difference(self, value):
        """Remove all values of the given attribute from the current range. 
        The result is a RangeSet object. The current range is left intact."""
        ranges = []
        if value.isempty():
            return RangeSet(self, itemtype=self.itemtype, interval=self.interval)
        # Remaining piece of self, smaller than value.min
        if self._cmpminmin(value) < 0:
            ranges.append(type(self)(self.min, value.min - self.interval, interval=self.interval))
        # Remaining piece of self, higher than value.max
        if self._cmpmaxmax(value) > 0:
            ranges.append(type(self)(value.max+self.interval, self.max, interval=self.interval))
        return RangeSet(ranges, itemtype=self.itemtype, interval=self.interval)
    def connected(self, value):
        """returns True if this datarange overlaps with or is directly in succesion with datarange value"""
        # Note: we thread any value as a discreteRange. So
        # DiscreteRange(5,6).connected(Range("[3-4>")) is True, 
        # despite that 4 is not actually part of Range("[3-4>").
        value = self._Range(value)
        if self.isempty() or value.isempty():
            return False
        return ((self.min <= value.max + self.interval) and (self.max + self.interval >= value.min))
    def __len__(self):
        if self.isempty():
            return 0
        else:
            return int((self.max - self.min)/self.interval)+1
    def __eq__(self, value):
        """value. x.__eq__(y) <==> x==y"""
        # Value may be anything, like None
        try:
            return (self.min == value.min) and (self.max == value.max) and \
                (self.itemtype == value.itemtype) and (self.interval == value.interval)
        except AttributeError:
            return False
    def __str__(self):
        if self.min == self.max:
            return "%s" % repr(self.min)
        else:
            return "%s-%s" % (repr(self.min), repr(self.max))
    def __repr__(self):
        append = ""
        if self.interval != 1:
            append += ", interval=%s" % self.interval
        if self.min == self.max:
            return "%s(%s%s)" % (type(self).__name__, repr(self.min), append)
        else:
            return "%s(%s,%s%s)" % (type(self).__name__, repr(self.min), repr(self.max), append)


# TODO: do we like to mix regular set items to mix in, or even None as a value? It can be useful as some 
# network layers (e.g. Ethernet) do not always have a labelvalue, and some (e.g. Fiber) even never.


class RangeSet(object):
    """A set of ordered items, stored in ranges. E.g. [6,8-15,24-32,48] 
    instead of [6,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,32,48]"""
    """The parts that make up the rangeset."""
    ranges          = None
    """Interval of the RangeSet. 0 for ContinuousRange objects, > 0 for DiscreteRange objects. Read only."""
    interval        = None   # If interval == 0: ContinuousRange, interval > 0: DiscreteRange
    """Individual items in the RangeSet. E.g. int, float, long, str or unicode. Read only."""
    itemtype        = None
    def __init__(self, string_or_array=None, interval=None, itemtype=None):
        """Create a new RangeSet. Examples: RangeSet("6,8-15,24-32,48",interval=1), 
        RangeSet(["[6]","[8-16>","[24-32]","48"]),
        RangeSet([6,DiscreteRange(8,15),DiscreteRange(24,32),48])
        """
        self.ranges = []
        if itemtype:
            self._setitemtype(itemtype)
        if interval != None:
            self._setinterval(interval)
        if string_or_array == None:
            pass
        elif isinstance(string_or_array, RangeSet): # type conversion: make a copy
            if not self.itemtype:
                self._setitemtype(string_or_array.itemtype)
            if not self.interval:
                self._setinterval(string_or_array.interval)
            for range in string_or_array: # we can loop through RangeSets to get the Range objects
                self.ranges.append(self._Range(range, alwayscopy=True))
        elif (type(string_or_array) in [str, unicode]) and (itemtype not in [str, unicode]):
            string_or_array = self._stringToList(string_or_array)
            for item in string_or_array:
                self.add(item)
        elif isinstance(string_or_array, list):
            for item in string_or_array:
                self.add(item)
        else:
            self.add(string_or_array)
    def _stringToList(self, rangestring):
        return rangestring.split(",")  # still includes spaces
    def _Range(self, item, item2=None, alwayscopy=False):
        """Verifies that the given item is a Range object with the correct type (ContinuousRange or DiscreteRange) 
        as required by self.interval, and make sure the other properties are the same as well (interval and itemtype). 
        If not, creates a copy with proper parameters. If alwayscopy is True, a copy will be made, even if the parameters 
        are fine."""
        if not (isinstance(item, Range) or (type(item) in [int, long, float, str, unicode])):
            raise AttributeError("item is of type %s, must be of type Range, int, long, float, or string" % type(item).__name__)
        if self.interval == 0: # item must be ContinuousRange
            if isinstance(item, ContinuousRange):
                if alwayscopy or (self.itemtype != item.itemtype):
                    return ContinuousRange(item.min, item.max, itemtype=self.itemtype, mininclusive=item.mininclusive, maxinclusive=item.maxinclusive)
                else:
                    return item
            elif isinstance(item, Range):
                return ContinuousRange(item.min, item.max, itemtype=self.itemtype, mininclusive=item.mininclusive, maxinclusive=item.maxinclusive)
            else:
                if item2:
                    return ContinuousRange(item, item2, itemtype=self.itemtype)
                else:
                    return ContinuousRange(item, itemtype=self.itemtype)
        elif self.interval != None: # item must be DiscreteRange
            if isinstance(item, DiscreteRange):
                if alwayscopy or (self.itemtype != item.itemtype) or (self.interval != item.interval):
                    return DiscreteRange(item.min, item.max, itemtype=self.itemtype, interval=self.interval)
                else:
                    return item
            elif isinstance(item, Range):
                if item.mininclusive and item.maxinclusive:
                    return DiscreteRange(item.min, item.max, interval=self.interval, itemtype=self.itemtype)
                else:
                    newrange = DiscreteRange(None, interval=self.interval, itemtype=self.itemtype)
                    newrange.mininclusive = item.mininclusive
                    newrange.maxinclusive = item.maxinclusive
                    newrange.setRange(item.min, item.max)
                    return newrange
            else:
                if item2:
                    return DiscreteRange(item, item2, interval=self.interval, itemtype=self.itemtype)
                else:
                    return DiscreteRange(item, interval=self.interval, itemtype=self.itemtype)
        else:  # nothing to compare against. simply make sure it is a valid Range object.
            if (type(item) == Range) or alwayscopy: # Range is abstract. turn into ContinuousRange
                if ((type(item) == Range) and (type(item.itemtype) in [int, long])) or type(item) in [int, long]:
                    self.interval = 1
                    return DiscreteRange(item, itemtype=self.itemtype)
                else:
                    self.interval = 0
                    return ContinuousRange(item, itemtype=self.itemtype)
            elif not isinstance(item, Range):
                if (type(item) in [int, long]) or ((type(item) == str) and item.isdigit()):
                    self.interval = 1
                    if item2:
                        return DiscreteRange(item, item2, interval=self.interval, itemtype=self.itemtype)
                    else:
                        return DiscreteRange(item, itemtype=self.itemtype)
                else:
                    self.interval = 0
                    if item2:
                        return ContinuousRange(item, item2, itemtype=self.itemtype)
                    else:
                        return ContinuousRange(item, itemtype=self.itemtype)
            else:
                return item
    def copy(self):
        """Return a copy of this set. The individual ranges are copied as well, the individual items are not."""
        return type(self)(self)
    def __copy__(self):
        """Return a copy of this set. The individual ranges are copied as well, the individual items are not."""
        return type(self)(self)
    def _simplify(self):
        """Merge the ranges in the set, if possible"""
        # before = "%s" % self
        # delete empty ranges
        i = 0
        while i < len(self.ranges):
            if self.ranges[i].isempty():
                del self.ranges[i]
            else:
                i += 1
        # merge continuous ranges
        i = 0
        self.ranges.sort(cmp=cmp)  # sort in place; require elaborate __cmp__, instead of default __lt__.
        while i < len(self.ranges)-1:
            if self.ranges[i].connected(self.ranges[i+1]):
                self.ranges[i].extend(self.ranges[i+1])
                del self.ranges[i+1]
            else:
                i += 1
        # print "simplify: %s ==> %s" % (before, self)
    def add(self, item, item2=None):
        """Add an element to the RangeSet. The element may be an item, Range or min,max"""
        # Make sure item is of the same type (DiscreteRange or ContinuousRange as the other elements)
        item = self._Range(item, item2=item2, alwayscopy=True)
        if item.isempty():
            return
        if not self.itemtype:
            self._setitemtype(item.itemtype)
            self._setinterval(item.interval)
        self.ranges.append(item)
        self._simplify()
    def _setitemtype(self, itemtype):
        if self.itemtype:
            return
        if itemtype in [int, float, long, str, unicode]:
            self.itemtype = itemtype
        else:
            raise ValueError("itemtype must be int, float, long, str or unicode, not %s" % itemtype)
    def _setinterval(self, interval):
        if not self.itemtype:
            self._setitemtype(type(interval))
        self.interval = self.itemtype(interval)
        if not (self.interval > 0):
            self.interval = self.itemtype(0)
    def append(self, item):
        """Add an element to the RangeSet. The element may be an item or a Range. Same as add()."""
        self.add(item)
    def update(self, rangeset):
        """Update the RangeSet to the union of itself and the given rangeset"""
        for range in rangeset:
            self.add(range)
    def union(self, rangeset):
        """Return a new rangeset, consisting of all elements in either this rangeset or the given rangeset."""
        newrangeset = self.copy()
        newrangeset.update(rangeset)
        return newrangeset
    def discard(self, item):
        """Remove the given element from this RangeSet. The element may be an item or a Range.
        Does nothing if the item does not exist."""
        # Make sure item is of the same type (DiscreteRange or ContinuousRange as the other elements)
        item = self._Range(item)
        if self.isempty() or item.isempty():
            return
        i = 0
        while i < len(self.ranges):
            if self.ranges[i].overlaps(item):
                newranges = self.ranges[i].difference(item)
                self.ranges[i:i+1] = newranges.ranges
            else:
                i += 1
        self._simplify()
    def difference_update(self, rangeset):
        """Remove all elements from the given rangeset from this rangeset."""
        for range in rangeset:
            self.discard(range)
    def difference(self, rangeset):
        """Return a new rangeset, consisting of all elements of this rangeset, except for those present in the given rangeset."""
        newrangeset = self.copy()
        newrangeset.difference_update(rangeset)
        return newrangeset
    def intersection_update(self, rangeset):
        """Update a set with the intersection of itself and another."""
        newrangeset = self.intersection(rangeset)
        self.ranges = newrangeset.ranges
    def intersection(self, rangeset):
        """Return the intersection of two sets as a new rangeset. (i.e. all elements that are in both sets.)"""
        newrangeset = type(self)(None, itemtype=self.itemtype, interval=self.interval)
        for selfrange in self.ranges:
            for valuerange in rangeset.ranges:
                if selfrange.overlaps(valuerange):
                    newrangeset.ranges.append(selfrange.intersection(valuerange))
        newrangeset._simplify()
        return newrangeset
    def symmetric_difference_update(self, rangeset):
        """Return the symmetric difference of two sets as a new rangeset. (i.e. all elements that are in exactly one of the sets.)"""
        newrangeset = self.symmetric_difference(rangeset)
        self.ranges = newrangeset.ranges
    def symmetric_difference(self, rangeset):
        """Update this rangeset with the symmetric difference of itself and another."""
        # Sym_diff(a,b) := (a - b) + (b - a)
        newrangeset1 = self - rangeset
        newrangeset2 = rangeset - self
        newrangeset1.update(newrangeset2)
        return newrangeset1
    def __sub__(self, rangeset):
        """x.__sub__(y) <==> x-y <==> difference() or copy()+discard()"""
        return self.difference(rangeset)
    def __isub__(self, rangeset):
        """x.__isub__(y) <==> x-=y <==> difference_update() or discard()"""
        self.difference_update(rangeset)
        return self
    def __add__(self, rangeset):
        """x.__add__(y) <==> x+y <==> union()"""
        return self.union(rangeset)
    def __iadd__(self, rangeset):
        """x.__iadd__(y) <==> x+=y <==> update()"""
        self.update(rangeset)
        return self
    def __or__(self, rangeset):
        """x.__or__(y) <==> x|y <==> union()"""
        return self.union(rangeset)
    def __ior__(self, rangeset):
        """x.__ior__(y) <==> x|=y <==> update()"""
        self.update(rangeset)
        return self
    def __xor__(self, rangeset):
        """x.__xor__(y) <==> x^y <==> symmetric_difference"""
        return self.symmetric_difference(rangeset)
    def __ixor__(self, rangeset):
        """x.__xor__(y) <==> x^=y <==> symmetric_difference_update"""
        self.symmetric_difference_update(rangeset)
        return self
    def __and__(self, rangeset):
        """x.__and__(y) <==> x&y <==> intersection()"""
        return self.intersection(rangeset)
    def __iand__(self, rangeset):
        """x.__and__(y) <==> x&=y <==> intersection_update()"""
        self.intersection_update(rangeset)
        return self
    def __getitem__(self, i): return self.ranges[i]
    def __setitem__(self, i, item): self.ranges[i] = item
    def __delitem__(self, i): del self.ranges[i]
    def isempty(self):
        """Returns True if there are no elements in the given range."""
        return len(self.ranges) == 0
    def __nonzero__(self):
        """x.__nonzero() <==> bool(x)"""
        return not self.isempty()
    def clear(self):
        """Removes all elements from this rangeset"""
        self.ranges = []
    def __contains__(self, value):
        for range in self.ranges:
            if value in range:
                return True
        return False
    def issubset(self, rangeset):
        """Report whether another set contains this set. (this < rangeset)"""
        newset = self - rangeset
        return newset.isempty()
    def issuperset(self, rangeset):
        """Report whether this set contains another set. (rangeset < this)"""
        newset = rangeset - self
        return newset.isempty()
    def overlaps(self, value):
        """returns True if this datarange overlaps with datarange or rangeset value"""
        if isinstance(value, RangeSet):
            for rangevalue in value.ranges:
                for range in self.ranges:
                    if range.overlaps(rangevalue):
                        return True
        else:
            for range in self.ranges:
                if range.overlaps(value):
                    return True
        return False
    def connected(self, value):
        """returns True if this datarange overlaps with or is directly in succesion with datarange or rangeset value"""
        if isinstance(value, RangeSet):
            for rangevalue in value.ranges:
                for range in self.ranges:
                    if range.connected(rangevalue):
                        return True
        else:
            for range in self.ranges:
                if range.connected(value):
                    return True
        return False
    def __eq__(self, value):
        """value. x.__eq__(y) <==> x==y"""
        if not isinstance(value, RangeSet):
            return False
        if len(self.ranges) != len(value.ranges):
            return False
        i = 0
        while i < len(self.ranges):
            if not (self.ranges[i] == value.ranges[i]):
                return False
            i += 1
        return True
    def __ne__(self, value):
        """x.__ne__(y) <==> x!=y"""
        return not self.__eq__(value)
    def __len__(self):
        """Returns the length of a given Range. Note that a length of 0 does not mean the RangeSet is empty. The length of a ContinuousRange [6-6] is 0, but it is not empty. Use isempty() to check for an empty RangeSet."""
        length = 0
        for range in self.ranges:
            length += len(range)
        return length
    def __str__(self):
        itemlist = []
        for item in self.ranges:
            itemlist.append(item.__str__())
        return "{" + ", ".join(itemlist) + "}"
    def __repr__(self):
        itemlist = []
        for item in self.ranges:
            itemlist.append(item.__repr__())
        return "%s([%s], interval=%s)" % (type(self).__name__, ", ".join(itemlist), self.interval)


