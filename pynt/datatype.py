# -*- coding: utf-8 -*-
"""Module for datatypes. This module defines value objects, type objects and 
type subclasses. In particular, this module defines Values (e.g. '3'), Ranges 
(e.g. '3-6') and RangeSets (e.g. '2,5-8,11'). Ranges have a dual nature. On 
one hand, they are a Type (range 0-1000 is a subType of all Integers), while 
one the other ranges are a value: Ranges and Values are items in a RangeSet.

Next to the generic Type and Value, we define generic subclasses:
Generic Types and Values  (e.g. a set of possible values)
  +- Ordered Values and Types  (e.g. Strings and Binary Data)
       +- Countable Values and Types  (e.g. Integers)
       +- Continuous Values and Types (e.g. Floats)

OrderedTypes can be compared, CountableType behave like sets, while 
ContinuousTypes have a length, and are not countable.

Type                        property    primitive   ordered     countable   continuous (1)
string                      Yes         Yes         Yes         No          Yes
hexBinary                   Yes         Yes         Yes         No          Yes
float                       Yes         Yes         Yes         No          Yes

None                        Yes         Yes         Yes (2)     Yes (2)     No
boolean                     Yes         Yes         Yes (2)     Yes (2)     No
integer                     Yes         Yes         Yes         Yes         No

string (fixed length)       Yes         Yes         Yes         Yes (3)     No
binary (fixed length)       Yes         Yes         Yes         Yes (3)     No
discrete float (4)          Yes         Yes         Yes         Yes         No
margin float (5)            Yes         Yes         Yes         Yes         No

item in set                 Yes         Yes (6)     No          No (7)      No

Range (8)                   Yes         No          Yes         No          No
ContinuousRange (8)         Yes         No          Yes         No          Yes
CountableRange (8)          Yes         No          Yes         Yes         No

RangeSet (9)                Yes (10)    Yes         Yes         No          No
ContinuousRangeSet (9)      Yes (10)    Yes         Yes         No          Yes
CountableRangeSet (9)       Yes (10)    Yes         Yes         Yes         No

(1) Countable are always discrete. Ordered and not-countable are always continuous.
    Continuous and discrete (including countable) are mutually exclusive.
(2) Technically, yes. Logically perhaps not, but we support it anyway.
(3) Practically, fixed length strings and binary are not countable, since 
    the count goes very fast: 4294967296**n for unicode, 256**n for binary for 
    lenght n.
(4) A discrete float is a float with restrictions on the allowed value. Values 
    must be n*interval, with n an integer, and interval a base interval.
(5) A margin float is a float with a certain 'bandwidth', meaning that no 
    other items are allowed within this range. This limits the number of 
    allows floats in a range.
(6) Depends on the elements in the set, but could be treated as primitive
(7) Items are discrete, but not ordered. Since we are only interested 
    in ordered and countable types, this is implemented as non-countable.
(8) A Range contains a minimum and maximum. A range is Both a Type and a Value!
    A value of a Range type is an element of it's primitive type (integer, string, float)
    A Range value is a specific value which is used in RangeSets.
    Example of ContinuousRange Types are string subsets (e.g. [A-B> is all strings 
    starting with an A), or float subsets (e.g. [3.0-4.0]). Examples of DiscreteRange 
    are integer subsets (e.g. [3-28]).
(9) A RangeSet is a compact list of allowed values. E.g. [2-6,8-13,15,19-23]
(10) Like all others types, the *value* of a RangeSet is a primitive value (integer, 
    float, string, etc.)

Technically a Range is a decorator class of the CountableType or OrderedType.
It's attributes are the (parent)type, min, and max. Range is also a DataValue 
subclass, with (min,max) as the value.

RangeSet is just a set, but some items may be a range object, and merged when 
adding sets. Also length is modified.

See also:
pynt.xmlns has a subclass of Value, NamedValue, which includes an URI identifier for Value.
pynt.xmlns has a subclass of Type, NamedType, which includes an URI identifier for Type.
Conversion to and from RDF is done in pynt.input.rdf and pynt.output.[manual]rdf.
"""

import math
import binascii
import types



class DataValue(object):
    """Any data value. This is a wrapper around primitive Python values, but the type 
    is dynamic instead of a static class. This allows very strict type checking. For 
    example a DataValue which can only take the value of a given item in a set."""
    def __init__(self, value, type):
        self.value = value              # holding the primitive Python value. Can be of any type, including tuplets.
        self.type  = type
    def isPrimitive(self):
        return (isinstance(self, PrimitiveValue))
    def isOrdered(self):
        return (isinstance(self, OrderedValue))
    def isCountable(self):
        return (isinstance(self, CountableValue))
    def isContinuous(self):
        return (isinstance(self, ContinuousValue))
    # Comparison methods
    def __eq__(self, cmpvalue):
        return (type(self) == type(cmpvalue)) and (self.type == cmpvalue.type) and (self.value == cmpvalue.value)
    def __ne__(self, cmpvalue):
        return not self.__eq__(cmpvalue)
    def __cmp__(self, cmpvalue):
        if not isinstance(cmpvalue, DataValue):
            raise TypeError("no ordering relation is defined between types %s and %s" % (self.type, type(cmpvalue)))
        elif not (self.type == cmpvalue.type):
            return cmp(self.type, cmpvalue.type)
        else:
            return cmp(self.value, cmpvalue.value)
            #raise TypeError("no ordering relation is defined for %s" % self.type)
    def __lt__(self, cmptype):
        try:
            return self.__cmp__(cmptype) < 0
        except TypeError:
            return False
    def __gt__(self, cmptype):
        try:
            return cmp(self, cmptype) > 0
        except TypeError:
            return False
    def __le__(self, cmptype):
        return self.__eq__(cmptype) or self.__lt__(cmptype)
    def __ge__(self, cmptype):
        return self.__eq__(cmptype) or self.__gt__(cmptype)
    # Arithmetic methods
    def __sub__(self, cmpvalue):
        raise TypeError("no countable relation is defined for %s" % self.type)
    # Output methods
    #def __str__(self):
    #    return "%s(%s)" % (self.type, self.type.toPrintable(self.value))
    def __str__(self):
        if isinstance(self.type, Type):
            return self.type.toPrintable(self.value)
        else:
            return str(self.value)
    #    return "%s(%s)" % (self.type, self.type.toPrintable(self.value))
    def __repr__(self):
        return "%s(%s)" % (repr(self.type), repr(self.value))
    def toPython(self):
        return self.value


class PrimitiveValue(DataValue):
    def __init__(self, value, type):
        # assert not hasattr(value, '__len__'), "Value %s must be a primitive (no list, dict or tuples)" % value # but string is OK
        DataValue.__init__(self, value, type)

class OrderedValue(DataValue):
    def __cmp__(self, cmpvalue):
        if not isinstance(cmpvalue, OrderedValue):
            raise TypeError("no ordering relation is defined between types %s and %s" % (self.type, type(cmpvalue).__name__))
        if self.type != cmpvalue.type:
            return cmp(self.type, cmpvalue.type)
        return self.type.compare(self.value, cmpvalue.value)

class CountableValue(OrderedValue):
    def __sub__(self, cmpvalue):
        if not isinstance(cmpvalue, CountableValue):
            raise TypeError("no countable relation is defined between types %s and %s" % (self.type, type(cmpvalue).__name__))
        if self.type != cmpvalue.type:
            raise TypeError("no countable relation is defined between types %s and %s" % (self.type, cmpvalue.type))
        return self.type.diff(self.value, cmpvalue.value)

class ContinuousValue(OrderedValue):
    modifier = 0    # value := value + modifier * epsilon, with epsilon an infitely small value.
    # A modifier allows exclusive values. E.g. the range 3-4, exclusive 4, would be 4, with modfifier -1. 
    def __init__(self, value, type, modifier=0):
        DataValue.__init__(self, value, type)
        self.modifier = int(modifier)
    # Comparison methods
    def __eq__(self, cmpvalue):
        return (type(self) == type(cmpvalue)) and (self.type == cmpvalue.type) and (self.value == cmpvalue.value) \
                and (self.modifier == cmpvalue.modifier)
    def __cmp__(self, cmpvalue):
        result = OrderedValue.__cmp__(self, cmpvalue)
        if result == 0:
            return cmp(self.modifier, cmpvalue.modifier)
        else:
            return result
    # Arithmetic methods
    def __sub__(self, cmpvalue):
        if isinstance(cmpvalue, DataValue):
            raise TypeError("no countable relation is defined between types %s and %s" % (self.type, type(cmpvalue.type).__name__))
        return self.value - cmpvalue.value
    # Output methods
    def __str__(self):
        if self.modifier == 0:
            return DataValue.__str__(self)
        elif self.modifier < 0:
            return "%s>" % DataValue.__str__(self)
        else:
            return "<%s" % DataValue.__str__(self)
    def __repr__(self):
        if self.modifier == 0:
            return "%s(%s)" % (repr(self.type), repr(self.value))
        elif self.modifier > 0:
            return "%s(%s,modifier=+1)" % (repr(self.type), repr(self.value))
        else:
            return "%s(%s,modifier=-1)" % (repr(self.type), repr(self.value))


class PrimitiveOrderedValue(OrderedValue, PrimitiveValue):
    pass

class PrimitiveCountableValue(CountableValue, PrimitiveValue):
    pass

class PrimitiveContinuousValue(ContinuousValue, PrimitiveValue):
    pass


class Type(object):
    """Type class. Instances of this class are datatypes. For example, string, 
    string of specific length, integer, integer subrange, etc."""
    # NOTE: this type was abstract, but it should be able to instantiated for types with no 
    # ordering or syntax checking whatsoever.
    default         = None
    valueclass      = DataValue
    primitivetype   = None
    def __init__(self):
        pass
        #raise NotImplementedError("%s is an abstract class." % type(self).__name__)
    def __call__(self, value=None, value2=None):
        """Make all type instances callable, just like a regular type.
        e.g. Type(2) gives a Value of type Type, and Type(1,2) and range of type Type."""
        if value2==None:
            return self.getValue(value)
        else:
            return self.getRange(value, value2)
    def getDefault(self):
        return self.default
    def getValue(self, value=None):
        """Create a value instance of the current type"""
        if value == None:
            value = self.getDefault()
        if not self.isvalidprimitivevalue(value):
            raise TypeError("%s is not a proper %s" % (value, self))
        value = self.toPrimitive(value)
        return self.getValueClass()(value, self)
    def getRange(self, min, max):
        """Create a range instance of the current type"""
        assert self.isOrderedType()
        if not self.isvalidprimitivevalue(min):
            raise TypeError("%s is not a proper %s" % (min, self))
        min = self.toPrimitive(min)
        if not self.isvalidprimitivevalue(max):
            raise TypeError("%s is not a proper %s" % (max, self))
        max = self.toPrimitive(max)
        if self.isContinuousType():
            return ContinuousRange(min, max, type=self)
        elif self.isCountableType():
            return CountableRange(min, max, type=self)
        else:
            return Range(min, max, type=self)
    def isPrimitiveType(self):
        """Return True if it can be represented as a single XML datatype (int, float, bool, etc.)"""
        return True
    def isOrderedType(self):
        """Return True if values are ordered: a < b is well defined (__cmp__ is implemented)"""
        return issubclass(self.getValueClass(), OrderedValue)
    def isCountableType(self):
        """Return True if it is countable: a - b gives an integer (__sub__ is implemented)"""
        return issubclass(self.getValueClass(), CountableValue)
    def isContinuousType(self):
        """Return True if it is continuous: for all a < b, there is always a value e in between: a < e < b"""
        return issubclass(self.getValueClass(), ContinuousValue)
    def getPrimitivetype(self):
        return self.primitivetype
    # Helper function of values
    def compare(self, value1, value2):
        """Compare value1 and value2. Both values are primitive types, not DataValue instances."""
        assert self.isOrderedType()
        return cmp(value1, value2)
    def diff(self, value1, value2):
        """value1 - value2. Both values are primitive types, not DataValue instances."""
        assert self.isCountableType()
        return (int(value1) - int(value2))
    def toPrintable(self, value):
        """Returns a printable representations"""
        return str(value)
    def isvalidprimitivevalue(self, value):
        """Return True if value is a primitve instance of the current Type (e.g. a string for String)"""
        if self.primitivetype:
            return isinstance(value, self.primitivetype)
        else:
            return True
    def toPrimitive(self, value, rounding=0):
        """Convert the given value to the primitive of this type"""
        if self.primitivetype:
            return self.primitivetype(value)
        else:
            return value
    def getValueClass(self):
        return self.valueclass
    # COMPARISON
    def __eq__(self, cmptype):
        """Test equality of two types (not the values)"""
        return type(self) == type(cmptype)
    def __ne__(self, cmptype):
        return not self.__eq__(cmptype)
    def __cmp__(self, cmptype):
        """Compare two types (not the values)"""
        if not isinstance(cmptype, Type):
            raise TypeError("no ordering relation is defined between types %s and %s" % (self, type(cmptype)))
        elif type(self) == type(cmptype):
            return 0
        else:
            return cmp(self.getPrimitivetype(), cmptype.getPrimitivetype())
    def __lt__(self, cmptype):
        try:
            return cmp(self, cmptype) < 0
        except TypeError:
            return False
    def __gt__(self, cmptype):
        try:
            return cmp(self, cmptype) > 0
        except TypeError:
            return False
    def __le__(self, cmptype):
        return self.__eq__(cmptype) or self.__lt__(cmptype)
    def __ge__(self, cmptype):
        return self.__eq__(cmptype) or self.__gt__(cmptype)
    # OUTPUT
    def __str__(self):
        return type(self).__name__
    def __repr__(self):
        return "%s.%s()" % (__name__,type(self).__name__)
    def toPython(self):
        return self.primitivetype


class OrderedType(Type):
    valueclass  = PrimitiveOrderedValue
    def __init__(self):
        pass

class ContinuousType(Type):
    valueclass  = PrimitiveContinuousValue
    def __init__(self):
        pass
    def __call__(self, value=None, value2=None, mininclusive=True, maxinclusive=True):
        """Make all type instances callable, just like a regular type"""
        if value2==None:
            if mininclusive and maxinclusive:
                return self.getValue(value, modifier=0)
            elif not mininclusive:
                return self.getValue(value, modifier=+1)
            else:
                return self.getValue(value, modifier=-1)
        else:
            if mininclusive and maxinclusive:
                return self.getRange(value, value2, minmodifier=0, maxmodifier=0)
            elif not mininclusive:
                return self.getRange(value, value2, minmodifier=+1, maxmodifier=0)
            else:
                return self.getRange(value, value2, minmodifier=0, maxmodifier=-1)
    def getDefault(self):
        return self.default
    def getValue(self, value=None, modifier=0):
        """Create a value instance of the current type"""
        if value == None:
            value = self.getDefault()
        if not self.isvalidprimitivevalue(value):
            raise TypeError("%s is not a proper %s" % (value, self))
        value = self.toPrimitive(value)
        return self.getValueClass()(value, self, modifier=modifier)
    def getRange(self, min, max, minmodifier=0, maxmodifier=0):
        """Create a range instance of the current type"""
        min = self.getValue(min, minmodifier)
        max = self.getValue(max, maxmodifier)
        if self.isContinuousType():
            return ContinuousRange(min, max, type=self)
        elif self.isCountableType():
            return CountableRange(min, max, type=self)
        else:
            return Range(min, max, type=self)

class CountableType(Type):
    def __init__(self):
        pass
    valueclass  = PrimitiveCountableValue


# PRIMITIVE, ORDERED, CONTINUOUS TYPES:

class StringType(ContinuousType):
    """Class of variable length string type"""
    default     = u""
    primitivetype = unicode
    def __init__(self):
        pass
    def isvalidprimitivevalue(self, value):
        return isinstance(value, (str, unicode))
    def __str__(self):
        return "String"  # shortcut defined in datatype module

String = StringType()

class BinaryType(ContinuousType):
    """Variable length binary type"""
    default     = ''
    primitivetype = str
    # Implementation notice: we now implement this as a binary string.
    # From Python 2.6 and onward, this should be implemented as a byte sequence, 
    # not by a unicode sequence!
    def __init__(self):
        pass
    def isvalidprimitivevalue(self, value):
        return isinstance(value, (str, int, long)) # str or byte. NOT UNICODE!
    def toPrimitive(self, value, rounding=0):
        """Convert e.g. 0xDEADC0FFEE (= 956397846510L) or '\xde\xad\xc0\xff\xee' to '\xde\xad\xc0\xff\xee'"""
        if isinstance(value, (long, int)):
            value = binascii.unhexlify("%x" % value) # 0xDEADC0FFEE => 'DEADC0FFEE' => '\xde\xad\xc0\xff\xee'
        else:
            assert isinstance(value, str) # str or byte. NOT UNICODE!
        return value
    def toPrintable(self, value):
        """Convert e.g.'\xde\xad\xc0\xff\xee' to 'DEADC0FFEE'"""
        return binascii.hexlify(value)
    def fromPrintable(self, value):
        """Convert e.g.'DEADC0FFEE' to '\xde\xad\xc0\xff\xee'"""
        return binascii.unhexlify(value)
    def toLong(self, value):
        """Convert e.g.'\xde\xad\xc0\xff\xee' to 0xDEADC0FFEE (= 956397846510L)."""
        result = 0L
        for i in range(len(value)):  # we're not using reduce(), since reduce() is deprecated
            result = 256*result + ord(value[i])
        return result

Binary = BinaryType()

class FloatType(ContinuousType):
    """Class of float type"""
    default     = 0.0
    primitivetype = float
    def __init__(self):
        pass
    def isvalidprimitivevalue(self, value):
        return isinstance(value, (float, int, long))

Float = FloatType()

# PRIMITIVE, ORDERED, COUNTABLE TYPES:

class NoneType(CountableType):
    """Class of None type"""
    default     = None
    primitivetype = types.NoneType
    def __init__(self):
        pass
    def __call__(self, value=None, value2=0):
        """Make all type instances callable, just like a regular type"""
        if value2 == 0:
            return self.getValue(value)
        else:
            return self.getRange(value, value2)
    def isvalidprimitivevalue(self, value):
        return value == None
    def toPrimitive(self, value, rounding=0):
        return None
    def diff(self, value1, value2):
        """value1 - value2. Since only one type exists, the result is always 0."""
        return 0

NoData = NoneType()

class BooleanType(CountableType):
    """Class of boolean type"""
    default     = False
    primitivetype = bool
    def __init__(self):
        pass
    def isvalidprimitivevalue(self, value):
        return value in (True, False, 1, 0)

Boolean = BooleanType()

class IntegerType(CountableType):
    """Class of integer type"""
    default     = 0
    primitivetype = int
    def __init__(self):
        pass
    def isvalidprimitivevalue(self, value):
        return isinstance(value, (int, long))

Integer = IntegerType()

# DERIVATE, ORDERED, COUNTABLE TYPES

class FixedLengthString(CountableType):
    """Fixed length unicode sequence type"""
    default     = u""
    primitivetype = unicode
    def __init__(self, length):
        assert isinstance(length, int)
        assert length >= 0
        self.length = int(length)
    def getDefault(self):
        return self.length*u" "
    def isvalidprimitivevalue(self, value):
        return isinstance(value, (str, unicode))
    def toPrimitive(self, value, rounding=0):
        """Convert to Unicode, and add spaces add the end"""
        value = unicode(value)
        if len(value) > self.length:
            raise ValueError("String %s is %d chars too long for type %s" % (self.toPrintable(value), \
                    len(value)-self.length, self.length))
        elif len(value) < self.length:
            value = value + (self.length - len(value))*u' '
        assert len(value) == self.length
        return value
    def toPrintable(self, value):
        """Convert to UTF-8"""
        return value.encode("utf-8")
    def toLong(self, value):
        """Convert Unicode sequence to UTF-32."""
        result = 0L
        for i in range(self.length):  # we're not using reduce(), since reduce() is deprecated
            result = 4294967296*result + ord(value[i])
        return result
    def __eq__(self, cmptype):
        return (type(self) == type(cmptype)) and (self.length == cmptype.length)
    def diff(self, value1, value2):
        """value1 - value2."""
        return (self.toLong(value1) - self.toLong(value2))
    def __cmp__(self, cmptype):
        """Compare two types (not the values)"""
        if not isinstance(cmptype, FixedLengthString):
            return PrimitiveType.__cmp__(self, cmptype)
        else:
            return cmp(self.length, cmptype.length)
    def __str__(self):
        return "%s(%d)" % (type(self).__name__, self.length)

class HexType(CountableType):
    """Fixed length binary type"""
    primitivetype = str
    # Implementation notice: we now implement this as a binary string.
    # From Python 2.6 and onward, this should be implemented as a byte sequence, 
    # not by a unicode sequence!
    def __init__(self, length):
        assert isinstance(length, int)
        assert length >= 0
        self.length = int(length)
    def getDefault(self):
        return self.length*chr(0)
    def isvalidprimitivevalue(self, value):
        return isinstance(value, (str, int, long)) # str or byte. NOT UNICODE!
    def toPrimitive(self, value, rounding=0):
        """Convert e.g. 0xDEADC0FFEE (= 956397846510L) or '\xde\xad\xc0\xff\xee' to '\xde\xad\xc0\xff\xee'"""
        if isinstance(value, (long, int)):
            value = binascii.unhexlify("%x" % value) # 0xDEADC0FFEE => 'DEADC0FFEE' => '\xde\xad\xc0\xff\xee'
        else:
            assert isinstance(value, str) # str or byte. NOT UNICODE!
        if len(value) > self.length:
            raise ValueError("Can not pack 0x%s of length %d in HexData of length %d" % (self.toPrintable(value), len(value), self.length))
        elif len(value) < self.length:
            value = (self.length - len(value))*'\x00' + value
        assert len(value) == self.length
        return value
    def toPrintable(self, value):
        """Convert e.g.'\xde\xad\xc0\xff\xee' to 'DEADC0FFEE'"""
        return binascii.hexlify(value)
    def fromPrintable(self, value):
        """Convert e.g.'DEADC0FFEE' to '\xde\xad\xc0\xff\xee'"""
        return binascii.unhexlify(value)
    def toLong(self, value):
        """Convert e.g.'\xde\xad\xc0\xff\xee' to 0xDEADC0FFEE (= 956397846510L)."""
        result = 0L
        for i in range(self.length):  # we're not using reduce(), since reduce() is deprecated
            result = 256*result + ord(value[i])
        return result
    def __eq__(self, cmptype):
        return (type(self) == type(cmptype)) and (self.length == cmptype.length)
    def diff(self, value1, value2):
        """value1 - value2."""
        ## assert self.countable
        return (self.toLong(value1) - self.toLong(value2))
    def __cmp__(self, cmptype):
        """Compare two types (not the values)"""
        if not isinstance(cmptype, HexType):
            return PrimitiveType.__cmp__(self, cmptype)
        else:
            return cmp(self.length, cmptype.length)
    def __str__(self):
        return "%s(%d)" % (type(self).__name__, self.length)

FourBytes    = HexType(4)   # E.g. for IPv4
SixBytes     = HexType(6)   # E.g. for MAC
SixteenBytes = HexType(16)  # E.g. for IPv6

class DiscreteFloat(CountableType):
    """Discrete Float Type, with restrictions on allowed values (must be n*interval, with n an integer)"""
    default     = 0.0
    primitivetype = float
    def __init__(self, interval):
        assert self.isvalidprimitivevalue(interval)
        assert interval > 0
        self.interval = float(interval)
    def isvalidprimitivevalue(self, value):
        return isinstance(value, (float, int, long))
    def toPrimitive(self, value, rounding=0):
        """0: rounds to nearest, 1: rounds up; -1: rounds down"""
        if rounding == 0:
            return round(float(value)/self.interval)*self.interval
        elif rounding < 0:
            return math.floor(float(value)/self.interval)*self.interval
        else: # round up
            return math.ceil(float(value)/self.interval)*self.interval
    def __eq__(self, cmptype):
        return (type(self) == type(cmptype)) and (self.interval == cmptype.interval)
    def __str__(self):
        return "%s(%f)" % (type(self).__name__, self.interval)
    def diff(self, value1, value2):
        """value1 - value2."""
        # assert self.countable
        return int(round((value1 - value2)/self.interval))
    def __cmp__(self, cmptype):
        """Compare two types (not the values)"""
        if not isinstance(cmptype, DiscreteFloat):
            return PrimitiveType.__cmp__(self, cmptype)
        else:
            return cmp(self.interval, cmptype.interval)

# TODO: margin float

# PRIMITIVE, UNORDERED TYPES:

class SetType(Type):
    """A set of items"""
    valueclass  = PrimitiveValue
    primitivetype = object
    def __init__(self, items=[]):
        assert isinstance(items, (list, set))
        self.items = set(items)
    def addAllowedItem(self, item):
        if item not in self.items:
            self.items.add(item)
    def getAllowedItems(self):
        return self.items
    def getDefault(self):
        raise NotImplemented("No default value defined for sets.")
    def isvalidprimitivevalue(self, value):
        return value in self.items
    def toPrimitive(self, value, rounding=0):
        return value
    def __eq__(self, cmptype):
        return (type(self) == type(cmptype)) and (self.items == cmptype.items)
    def __cmp__(self, cmptype):
        """Compare two types (not the values)"""
        if not isinstance(cmptype, SetType):
            return PrimitiveType.__cmp__(self, cmptype)
        else:
            return cmp(self.items, cmptype.items)

EmptySet = SetType([])

# NON-PRIMITIVE TYPES

class RangeType(OrderedType):
    # ranges are both a type (e.g. integer subset) and a value (e.g. item in RangeSet)!
    # note: order of parent classes is important! Methods in first class take precedence.
    # technically, RangeType is decorator of the Type class.
    """The abstract class of a Range Type. It is supposed to be mixed with a DataValue class."""
    primitivetype = tuple
    def __init__(self, min, max, type=None):
        """Initialize a Range. min, max are either primitive types, which are converted to Type type.
        Alternatively, min, max are DataValues of the same type."""
        if not isinstance(min, DataValue):
            if not isinstance(type, Type):
                raise TypeError("Arguments min,max of RangeType must be DataValues, or type a Type.")
            min = type(min)
        if not isinstance(max, DataValue):
            if not isinstance(type, Type):
                raise TypeError("Arguments min,max of RangeType must be DataValues, or type a Type.")
            max = type(max)
        if not min.type == max.type:
            raise TypeError("Arguments min,max of RangeType must be DataValues of the same type.")
        if min > max:
            raise ValueError("min %s > max %s" % (min,max))
        self.type  = min.type
        self.min   = min              # holding the DataValue instance.
        self.max   = max              # holding the DataValue instance.
    
    def clear(self):                        # NEED REVIEW
        """Removes all elements from this rangeset"""
        self.mininclusive = True
        self.maxinclusive = True
        self.min = None
        self.max = None
    
    def isvalidprimitivevalue(self, value):
        return self.type.isvalidprimitivevalue(value) and value >= self.min.value and value <= self.max.value
    
    def toPrimitive(self, value, rounding=0):
        return self.type.toPrimitive(value, rounding=rounding)
    
    def getDefault(self):
        return self.min.value
    
    def getValueClass(self):
        return self.type.getValueClass()
    
    def isPrimitiveType(self):
        """Return True if values can be represented as a single Python type."""
        return False
    
    # Helper function of values
    def toPrintable(self, value):
        """Returns a printable representations"""
        return self.type.toPrintable(value)
    
    def compare(self, value1, value2):
        """Compare value1 and value2. Both values are primitive types, not DataValue instances."""
        return self.type.compare(value1, value2)
    
    def diff(self, value1, value2):
        """value1 - value2. Both values are primitive types, not DataValue instances."""
        return self.type.diff(value1, value2)
    
    # Comparison
    def __eq__(self, cmprange):
        """value. x.__eq__(y) <==> x==y"""
        return (type(self) == type(cmprange)) and (self.min == cmprange.min) and (self.max == cmprange.max)
    
    def __ne__(self, value):
        """x.__ne__(y) <==> x!=y"""
        return not self.__eq__(value)
    
    def __cmp__(self, cmpvalue):
        if not isinstance(cmpvalue, OrderedValue):
            raise TypeError("no ordering relation is defined between types %s and %s" % (self.type, type(cmpvalue).__name__))
        if self.type != cmpvalue.type:
            raise TypeError("no ordering relation is defined between types %s and %s" % (self.type, cmpvalue.type))
        return self.type.compare(self.min.value, cmpvalue.min.value) or self.type.compare(self.max.value, cmpvalue.max.value)
        # The "or" results that the difference between min takes precedence over the difference in max.
    
    def X__cmp__(self, value):              # DUPLICATE
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
    
    def __gt__(self,cmpvalue):
        """x.__gt__(y) <==> x>y. return True if value y is a datarange or value smaller then the datarange x."""
        if isinstance(cmpvalue, RangeType):
            return self.min > cmpvalue.max
        else:
            return self.min > cmpvalue
    
    def __lt__(self,cmpvalue):
        """x.__lt__(y) <==> x<y. return True if value y is a datarange or value bigger then the datarange x."""
        # print "__lt__(%s,%s)" % (self,cmpvalue)
        if isinstance(cmpvalue, RangeType):
            return self.max < cmpvalue.min
        else:
            return self.max < cmpvalue
    
    def __le__(self, value):
        """x.__le__(y) <==> x<=y.
        return True if value y is a datarange or value smaller then or overlapping the datarange x.
        This is equivalent to (x < y) or x.overlap(y), thus not equivalent to (x < y) or (x == y)."""
        return not self.__gt__(value)
    
    def __ge__(self, value):
        """x.__le__(y) <==> x>=y. 
        return True if value y is a datarange or value bigger then or overlapping the datarange x.
        This is equivalent to (x > y) or x.overlap(y), thus not equivalent to (x > y) or (x == y)."""
        return not self.__lt__(value)
    
    # Arithmetic functions
    def union(self, value):
        """Return a union of the given attribute and the current range. 
        The result is a RangeSet object. The current range is left intact."""
        range = self.copy()
        return RangeSet([range,value])
    
    def difference(self, value):            # NEED REVIEW
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
    
    def intersection(self, value):          # NEED REVIEW
        """Remove the intersection of the given attribute and the current range. 
        The result is a Range object. The current range is left intact."""
        newrange = self.copy()
        newrange.intersection_update(value)
        return newrange
    
    def intersection_update(self, value):   # NEED REVIEW
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
    
    def issubset(self, value):              # NEED REVIEW
        """Value is another range. Returns True if this range is complete covered by the given range."""
        return (self._cmpminmin(value) >= 0) and (self._cmpmaxmax(value) <= 0)
    
    def issuperset(self, value):            # NEED REVIEW
        """Value is another range. Returns True if the give range is complete covered by this range."""
        return (self._cmpminmin(value) <= 0) and (self._cmpmaxmax(value) >= 0)
    
    def __contains__(self, value):          # NEED REVIEW
        if self.isempty():
            return False
        return (value >= self.min) and (value <= self.max)
    
    def overlaps(self, value):              # NEED REVIEW
        """returns True if this datarange overlaps with datarange value"""
        return not (self.__lt__(value) or self.__gt__(value))
    
    def connected(self, value):             # NEED REVIEW
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
    
    def __len__(self):                      # NEED REVIEW
        """Returns the length of a given Range. Note that a length of 0 does not mean the RangeSet is empty. The length of a ContinuousRange [6-6] is 0, but it is not empty. Use isempty() to check for an empty RangeSet."""
        # print "calling __len__"
        if self.isempty():
            return 0
        else:
            return self.max - self.min
    
    def isempty(self):
        return self.min == None
    def __nonzero__(self):
        """x.__nonzero() <==> bool(x)"""
        return not self.isempty()
    
    # Arithmetic helpers
    def _cmpminmin(self, value):            # NEED REVIEW
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
    
    def _cmpminmax(self, value):            # NEED REVIEW
        """Compare self.min and value.max. Note that None < i holds for all values of i"""
        if self.min == value.max:
            if self.mininclusive and value.maxinclusive:
                return 0
            else:
                return 1
        else:
            return cmp(self.min, value.max)
    
    def _cmpmaxmin(self, value):            # NEED REVIEW
        """Compare self.max and value.min. Note that None < i holds for all values of i"""
        if self.max == value.min:
            if self.maxinclusive and value.mininclusive:
                return 0
            else:
                return -1
        else:
            return cmp(self.max, value.min)
    
    def _cmpmaxmax(self, value):            # NEED REVIEW
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
    
    # Output of type
    def __str__(self):
        return "%s(%s,%s)" % (type(self).__name__, self.type.toPrintable(self.min.value), self.type.toPrintable(self.max.value))
    def __repr__(self):
        return "%s(%s,%s)" % (type(self).__name__, repr(self.min), repr(self.max))
    
    def toPython(self):
        return (self.min,self.max)          # for Range
    #def toPython(self):
    #    return self.type.toPython()         # for Type
    


class Range(RangeType, OrderedValue):
    # note: order of parent classes is important! Methods in first class take precedence.
    # We need a separate Range and RangeType class because we don't want CountableRange and 
    # ContinuousRange to be a subclass of OrderedValue via the Range(Type) class.
    """Any range data value. This is a efficient storage for a list of data values.
    The primitive datatype must be ordered. Thus IntegerRange(3,7) is treated as
    [Integer(3), Integer(4), Integer(5), Integer(6) and Integer(7)]."""
    def __init__(self, min, max, type):
        RangeType.__init__(self, min, max, type)

class CountableRange(RangeType, CountableValue):
    # note: order of parent classes is important! Methods in first class take precedence.
    """Ranges are an efficient storage for a list of data values. 
    For example IntegerRange 3-7 is treated as IntegerType 3, 4, 5, 6 and 7.
    The primitive datatype for CountableRanges must be countable. This is the 
    range to use for Integers, DiscreteFloat . """
    def __init__(self, min, max, type):
        assert(isinstance(type, Type))
        if not type.isvalidprimitivevalue(min):
            raise TypeError("%s is not a proper %s" % (min, type))
        min = type.toPrimitive(min, rounding=1)
        if not type.isvalidprimitivevalue(max):
            raise TypeError("%s is not a proper %s" % (max, type))
        max = type.toPrimitive(max, rounding=-1)
        RangeType.__init__(self, min, max, type)
    def __sub__(self, cmpvalue):
        if not isinstance(cmpvalue, CountableValue):
            raise TypeError("no countable relation is defined between types %s and %s" % (self.type, type(cmpvalue).__name__))
        if self.type != cmpvalue.type:
            raise TypeError("no countable relation is defined between types %s and %s" % (self.type, cmpvalue.type))
        return self.type.diff(self.min.value, cmpvalue.min.value) # TODO: pass (self.min, cmpvalue.min) (DataValue instead of value)
    #def diff(self, value1, value2):
    #    """value1 - value2."""
    #    # assert self.countable
    #    return int(round((value1 - value2)/self.type.interval))
    # TODO: fix __str__
    #def __str__(self):
    #    return "%s(%f,%f,%f)" % (type(self).__name__, self.min, self.max, self.type.interval)

# DiscreteRange is an alias for CountableRange
DiscreteRange = CountableRange

class ContinuousRange(RangeType, ContinuousValue):
    # note: order of parent classes is important! Methods in first class take precedence.
    mininclusive = True
    maxinclusive = True
    def __init__(self, min, max, type, mininclusive=True, maxinclusive=True):
        RangeType.__init__(self, min, max, type)
    #def __sub__(self, cmpvalue):
    #    if isinstance(cmpvalue, DataValue):
    #        raise TypeError("no countable relation is defined between types %s and %s" % (self.type, type(cmpvalue.type).__name__))
    #    raise TypeError("no countable relation is defined between types %s and %s" % (self.type, type(cmpvalue).__name__))
    


class IntegerRange(CountableRange):
    """Integer Type, with restrictions on value. Values must be in (min, max)"""
    valueclass  = PrimitiveCountableValue
    def __init__(self, min, max):
        CountableRange.__init__(self, min, max, IntegerType())

class FloatRange(ContinuousRange):  # TODO: change to ContinuousRange
    """Float Type, with restrictions on value. Values must be in (min, max)"""
    def __init__(self, min, max):
        ContinuousRange.__init__(self, min, max, FloatType())

class DiscreteFloatRange(CountableRange):  # TODO: change to CountableRange
    """Float Type, with restrictions on value. 
    Values must be n*interval, with n an integer, and in the range (min, max)"""
    def __init__(self, min, max, interval):
        CountableRange.__init__(self, min, max, DiscreteFloat(interval))
    def __str__(self):
        return "%s(%f,%f,%f)" % (type(self).__name__, self.min.value, self.max.value, self.type.interval)


# TODO: implement rangesets

class RangeSet(Type):
    """Rangeset Type. Values in the set may be single values or ranges."""
    pass

class ContinuousRangeSet(Type):
    """Continuous Rangeset Type. All values are float ranges."""
    pass

class CountableRangeSet(Type):
    """Countable rangeset Type. All values are countable values or countable ranges."""
    pass




def toDataValue(value):
    """Takes a primitive Python type, and converts it to a Value instance, as
    defined in this class."""
    pass

def _isinstance(value, type):
    return (value.type == type)
